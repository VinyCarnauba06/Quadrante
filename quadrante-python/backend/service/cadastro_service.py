from dataclasses import dataclass
from typing import Optional

from backend.domain.condominio import Condominio, GEOCODE_OK
from backend.domain.fiscal import Fiscal
from backend.domain.geocodificacao import ResultadoGeocodificacao
from backend.domain.rota import GeoPonto
from backend.service.geocoding_service import Geocodificador
from backend.service.routing_service import haversine_metros

CENTRO_ATUACAO = GeoPonto(id="", latitude=-9.6498, longitude=-35.7089)
RAIO_ATUACAO_METROS = 60000
TAMANHO_MAXIMO_NOME = 120
TAMANHO_MAXIMO_ENDERECO = 300
TAMANHO_MINIMO_BUSCA = 3


class DadosInvalidosError(ValueError):
    pass


class SemFiscalParaCadastroError(Exception):
    pass


@dataclass(frozen=True)
class Destino:
    fiscal: Fiscal
    distancia_metros: float


@dataclass(frozen=True)
class Candidato:
    resultado: ResultadoGeocodificacao
    destino: Optional[Destino]


class CadastroService:
    def __init__(self, store, geocodificador: Geocodificador):
        self._store = store
        self._geocodificador = geocodificador

    def localizar(self, texto: str, limite: int = 5) -> list[Candidato]:
        texto = (texto or "").strip()
        if len(texto) < TAMANHO_MINIMO_BUSCA:
            raise DadosInvalidosError(f"Digite ao menos {TAMANHO_MINIMO_BUSCA} caracteres do endereço.")
        resultados = self._geocodificador.buscar(texto, limite)
        return [Candidato(resultado=r, destino=self._destino_para(r.latitude, r.longitude)) for r in resultados]

    def cadastrar(self, nome: str, endereco: str, latitude: float, longitude: float) -> tuple[Condominio, Destino]:
        nome = (nome or "").strip()
        endereco = (endereco or "").strip()
        self._validar(nome, endereco, latitude, longitude)
        destino = self._destino_para(latitude, longitude)
        if destino is None:
            raise SemFiscalParaCadastroError("Nenhum fiscal de campo com carteira geocodificada para receber o condomínio.")
        condominio = self._store.adicionar_condominio(nome, endereco, latitude, longitude, destino.fiscal.id)
        return condominio, destino

    def _validar(self, nome: str, endereco: str, latitude: float, longitude: float) -> None:
        if not nome:
            raise DadosInvalidosError("Informe o nome do condomínio.")
        if len(nome) > TAMANHO_MAXIMO_NOME:
            raise DadosInvalidosError(f"O nome deve ter no máximo {TAMANHO_MAXIMO_NOME} caracteres.")
        if len(endereco) > TAMANHO_MAXIMO_ENDERECO:
            raise DadosInvalidosError(f"O endereço deve ter no máximo {TAMANHO_MAXIMO_ENDERECO} caracteres.")
        if isinstance(latitude, bool) or isinstance(longitude, bool) or not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            raise DadosInvalidosError("Coordenadas inválidas.")
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or (latitude == 0 and longitude == 0):
            raise DadosInvalidosError("Coordenadas inválidas.")
        ponto = GeoPonto(id="", latitude=latitude, longitude=longitude)
        if haversine_metros(CENTRO_ATUACAO, ponto) > RAIO_ATUACAO_METROS:
            raise DadosInvalidosError("O endereço está fora da área de atuação (Maceió e região).")

    def _destino_para(self, latitude: float, longitude: float) -> Optional[Destino]:
        ponto = GeoPonto(id="", latitude=latitude, longitude=longitude)
        carga = self._store.carga_por_fiscal()
        opcoes = []
        for fiscal in self._store.fiscais_de_campo(somente_ativos=True):
            try:
                centro_lat, centro_lng = self._store.centroide_da_carteira(fiscal.id)
            except Exception:
                continue
            distancia = haversine_metros(ponto, GeoPonto(id="", latitude=centro_lat, longitude=centro_lng))
            opcoes.append((distancia, carga.get(fiscal.id, 0), fiscal.id, fiscal))
        if not opcoes:
            return None
        distancia, _, _, fiscal = min(opcoes, key=lambda o: o[:3])
        return Destino(fiscal=fiscal, distancia_metros=distancia)
