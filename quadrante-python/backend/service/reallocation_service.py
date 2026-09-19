"""Alocação gulosa com limite de carga — porta fiel de
internal/service/reallocation_service.go: quando um fiscal entra em
ausência, sua carteira é distribuída entre os fiscais de campo ativos mais
próximos geograficamente, com desempate determinístico multi-chave.
"""

from dataclasses import dataclass, field
from datetime import datetime

from backend.domain.ausencia import Ausencia, Realocacao
from backend.domain.fiscal import PAPEL_COORDENADOR
from backend.domain.rota import GeoPonto
from backend.service.routing_service import haversine_metros, RoutingService

MAX_CONDOMINIOS_EXTRA_PADRAO = 6


class SemFiscalDisponivelError(Exception):
    pass


@dataclass
class _Opcao:
    fiscal_id: str
    distancia: float
    carga: int


@dataclass
class SolicitacaoAusencia:
    """Item que entra na Fila FIFO — o coordenador pode registrar várias
    ausências de uma vez; são processadas na ordem em que chegaram."""

    fiscal_id: str
    data_inicio: datetime
    data_fim: datetime
    motivo: str = "outro"
    observacao: str = ""


@dataclass
class ResultadoRealocacao:
    ausencia: Ausencia
    realocacoes: list = field(default_factory=list)


class ReallocationService:
    def __init__(self, store, routing: RoutingService, max_extra: int = MAX_CONDOMINIOS_EXTRA_PADRAO):
        self._store = store
        self._routing = routing
        self._max_extra = max_extra

    def registrar_ausencia(
        self,
        fiscal_id: str,
        data_inicio: datetime,
        data_fim: datetime,
        motivo: str = "outro",
        observacao: str = "",
    ) -> ResultadoRealocacao:
        ausencia = self._store.criar_ausencia(
            Ausencia(id="", fiscal_id=fiscal_id, data_inicio=data_inicio, data_fim=data_fim, motivo=motivo, observacao=observacao)
        )

        condominios_do_fiscal = self._store.listar_por_fiscal(fiscal_id)
        candidatos = self._fiscais_disponiveis(fiscal_id, data_inicio)
        if not candidatos:
            raise SemFiscalDisponivelError(f"nenhum fiscal disponível para cobrir a carteira de {fiscal_id}")

        carga_atual: dict[str, int] = {}
        realocacoes_feitas = []
        fiscais_afetados = {fiscal_id}

        for condominio in condominios_do_fiscal:
            if not condominio.tem_localizacao():
                continue

            destino, distancia = self._escolher_fiscal_mais_proximo(condominio, candidatos, carga_atual)
            if destino is None:
                continue

            self._store.atualizar_fiscal_titular(condominio.id, destino)

            realocacao = self._store.criar_realocacao(
                Realocacao(
                    id="",
                    ausencia_id=ausencia.id,
                    condominio_id=condominio.id,
                    fiscal_origem_id=fiscal_id,
                    fiscal_destino_id=destino,
                    distancia_metros=distancia,
                )
            )
            realocacoes_feitas.append(realocacao)
            carga_atual[destino] = carga_atual.get(destino, 0) + 1
            fiscais_afetados.add(destino)

        for afetado in fiscais_afetados:
            self._routing.gerar_rota_do_dia(afetado, datetime.utcnow())

        return ResultadoRealocacao(ausencia=ausencia, realocacoes=realocacoes_feitas)

    def _fiscais_disponiveis(self, fiscal_ausente_id: str, data_inicio: datetime):
        ativos = self._store.listar(somente_ativos=True)
        ausentes_na_data = self._store.listar_ativas_em(data_inicio)
        ausente_set = {a.fiscal_id for a in ausentes_na_data}

        return [
            f
            for f in ativos
            if f.id != fiscal_ausente_id and f.id not in ausente_set and f.papel != PAPEL_COORDENADOR
        ]

    def _escolher_fiscal_mais_proximo(self, condominio, candidatos, carga_atual: dict[str, int]):
        opcoes = []
        for f in candidatos:
            try:
                lat, lng = self._store.centroide_da_carteira(f.id)
            except Exception:
                continue
            d = haversine_metros(
                GeoPonto(id="", latitude=condominio.latitude, longitude=condominio.longitude),
                GeoPonto(id="", latitude=lat, longitude=lng),
            )
            opcoes.append(_Opcao(fiscal_id=f.id, distancia=d, carga=carga_atual.get(f.id, 0)))

        if not opcoes:
            return None, 0.0

        opcoes.sort(key=lambda o: (o.distancia, o.carga, o.fiscal_id))

        for o in opcoes:
            if carga_atual.get(o.fiscal_id, 0) < self._max_extra:
                return o.fiscal_id, o.distancia

        return opcoes[0].fiscal_id, opcoes[0].distancia

    def reverter_expiradas(self, hoje: datetime) -> int:
        expiradas = self._store.listar_expiradas(hoje)
        fiscais_afetados = set()

        for r in expiradas:
            self._store.atualizar_fiscal_titular(r.condominio_id, r.fiscal_origem_id)
            self._store.reverter(r.id)
            fiscais_afetados.add(r.fiscal_origem_id)
            fiscais_afetados.add(r.fiscal_destino_id)

        for afetado in fiscais_afetados:
            self._routing.gerar_rota_do_dia(afetado, hoje)

        return len(expiradas)

    # ---- fila de solicitações (FIFO) ---------------------------------------

    def enfileirar_solicitacao(self, solicitacao: SolicitacaoAusencia) -> int:
        self._store.fila_solicitacoes_ausencia.enfileirar(solicitacao)
        return len(self._store.fila_solicitacoes_ausencia)

    def processar_proxima_solicitacao(self) -> ResultadoRealocacao:
        solicitacao: SolicitacaoAusencia = self._store.fila_solicitacoes_ausencia.desenfileirar()
        return self.registrar_ausencia(
            solicitacao.fiscal_id,
            solicitacao.data_inicio,
            solicitacao.data_fim,
            solicitacao.motivo,
            solicitacao.observacao,
        )

    # ---- desfazer manual (LIFO, via Pilha do Store) ------------------------

    def desfazer_ultima_realocacao(self):
        return self._store.desfazer_ultima_realocacao()
