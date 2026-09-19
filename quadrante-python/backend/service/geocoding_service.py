from typing import Protocol

from backend.domain.geocodificacao import ResultadoGeocodificacao


class GeocodificacaoIndisponivelError(Exception):
    pass


class GeocodificacaoFalhouError(Exception):
    pass


class Geocodificador(Protocol):
    def buscar(self, texto: str, limite: int = 5) -> list[ResultadoGeocodificacao]: ...


class GeocodificadorAusente:
    def buscar(self, texto: str, limite: int = 5) -> list[ResultadoGeocodificacao]:
        raise GeocodificacaoIndisponivelError("Geocodificação não configurada. Preencha GEOAPIFY_API_KEY no .env e reinicie o servidor.")
