"""Redistribuição geográfica GERAL da carteira — porta fiel de
internal/service/clustering_service.go: k-means geográfico (Lloyd) com
centróides iniciais não-aleatórios (a posição atual de cada fiscal) + passo
de rebalanceamento de carga.
"""

from dataclasses import dataclass
from typing import Optional

from backend.domain.clustering import AtribuicaoSugerida, SugestaoClustering
from backend.domain.rota import GeoPonto
from backend.service.routing_service import haversine_metros

MAX_ITERACOES_KMEANS = 50
TOLERANCIA_BALANCEAMENTO = 1.3  # um cluster não pode passar de 130% do tamanho médio
DELTA_CONVERGENCIA_KMEANS_METROS = 5.0


@dataclass
class _PontoCluster:
    condominio: object
    geo: GeoPonto


class SemFiscalDeCampoError(Exception):
    pass


class SemCondominioGeocodificadoError(Exception):
    pass


class SemCentroideInicialError(Exception):
    pass


class ClusteringService:
    def __init__(self, store):
        self._store = store

    def sugerir_redistribuicao(self) -> SugestaoClustering:
        fiscais_campo = self._store.fiscais_de_campo()
        if not fiscais_campo:
            raise SemFiscalDeCampoError("nenhum fiscal de campo ativo")

        condominios_geo = self._store.listar_todos_geocodificados()
        ids_fiscal_campo = {f.id for f in fiscais_campo}

        pontos = [
            _PontoCluster(
                condominio=c,
                geo=GeoPonto(id=c.id, latitude=c.latitude, longitude=c.longitude),
            )
            for c in condominios_geo
            if c.fiscal_titular_id in ids_fiscal_campo and c.tem_localizacao()
        ]
        if not pontos:
            raise SemCondominioGeocodificadoError("nenhum condomínio geocodificado de fiscal de campo")

        centroides = self._centroides_iniciais(fiscais_campo)

        atribuicao_idx = _k_means_geografico(pontos, centroides)
        _rebalancear(pontos, atribuicao_idx, centroides)

        return self._montar_sugestao(fiscais_campo, pontos, atribuicao_idx)

    def aplicar_redistribuicao(self, atribuicoes: list[AtribuicaoSugerida]) -> int:
        aplicadas = 0
        for a in atribuicoes:
            if not a.mudou or not a.fiscal_sugerido_id:
                continue
            self._store.atualizar_fiscal_titular(a.condominio_id, a.fiscal_sugerido_id)
            aplicadas += 1
        return aplicadas

    def _centroides_iniciais(self, fiscais_campo) -> list[GeoPonto]:
        centroides: list[Optional[GeoPonto]] = [None] * len(fiscais_campo)
        soma_lat = soma_lng = 0.0
        com_carteira = 0

        for i, f in enumerate(fiscais_campo):
            try:
                lat, lng = self._store.centroide_da_carteira(f.id)
            except Exception:
                centroides[i] = None
                continue
            centroides[i] = GeoPonto(id=f.id, latitude=lat, longitude=lng)
            soma_lat += lat
            soma_lng += lng
            com_carteira += 1

        if com_carteira == 0:
            raise SemCentroideInicialError("nenhum fiscal de campo tem carteira geocodificada")

        media_lat, media_lng = soma_lat / com_carteira, soma_lng / com_carteira
        for i, f in enumerate(fiscais_campo):
            if centroides[i] is None:
                centroides[i] = GeoPonto(id=f.id, latitude=media_lat, longitude=media_lng)
        return centroides

    def _montar_sugestao(self, fiscais_campo, pontos: list[_PontoCluster], atribuicao: list[int]) -> SugestaoClustering:
        sugestao = SugestaoClustering(total_condominios=len(pontos))
        nomes_por_id = {f.id: f.nome for f in fiscais_campo}

        for i, p in enumerate(pontos):
            fiscal_sugerido = fiscais_campo[atribuicao[i]]
            mudou = p.condominio.fiscal_titular_id != fiscal_sugerido.id
            if mudou:
                sugestao.total_mudancas += 1

            sugestao.atribuicoes.append(
                AtribuicaoSugerida(
                    condominio_id=p.condominio.id,
                    condominio_nome=p.condominio.nome,
                    fiscal_atual_id=p.condominio.fiscal_titular_id,
                    fiscal_atual_nome=nomes_por_id.get(p.condominio.fiscal_titular_id, ""),
                    fiscal_sugerido_id=fiscal_sugerido.id,
                    fiscal_sugerido_nome=fiscal_sugerido.nome,
                    mudou=mudou,
                )
            )
        return sugestao


def _centroide_mais_proximo(p: GeoPonto, centroides: list[GeoPonto]) -> int:
    melhor, melhor_dist = 0, haversine_metros(p, centroides[0])
    for i in range(1, len(centroides)):
        d = haversine_metros(p, centroides[i])
        if d < melhor_dist:
            melhor, melhor_dist = i, d
    return melhor


def _recalcular_centroides(pontos: list[_PontoCluster], atribuicao: list[int], anteriores: list[GeoPonto]) -> list[GeoPonto]:
    k = len(anteriores)
    soma_lat = [0.0] * k
    soma_lng = [0.0] * k
    qtd = [0] * k

    for i, p in enumerate(pontos):
        cluster = atribuicao[i]
        soma_lat[cluster] += p.geo.latitude
        soma_lng[cluster] += p.geo.longitude
        qtd[cluster] += 1

    novos = []
    for i in range(k):
        if qtd[i] == 0:
            novos.append(anteriores[i])
            continue
        novos.append(GeoPonto(id=anteriores[i].id, latitude=soma_lat[i] / qtd[i], longitude=soma_lng[i] / qtd[i]))
    return novos


def _k_means_geografico(pontos: list[_PontoCluster], centroides: list[GeoPonto]) -> list[int]:
    atribuicao = [0] * len(pontos)

    for _ in range(MAX_ITERACOES_KMEANS):
        for i, p in enumerate(pontos):
            atribuicao[i] = _centroide_mais_proximo(p.geo, centroides)

        novos_centroides = _recalcular_centroides(pontos, atribuicao, centroides)
        deslocamento_maximo = max(
            (haversine_metros(centroides[i], novos_centroides[i]) for i in range(len(centroides))),
            default=0.0,
        )
        centroides = novos_centroides

        if deslocamento_maximo < DELTA_CONVERGENCIA_KMEANS_METROS:
            break

    for i, p in enumerate(pontos):
        atribuicao[i] = _centroide_mais_proximo(p.geo, centroides)
    return atribuicao


def _cluster_vizinho_com_folga(p: GeoPonto, centroides: list[GeoPonto], contagem: list[int], limite_maximo: int, excluir: int) -> int:
    melhor, melhor_dist = -1, -1.0
    for i, c in enumerate(centroides):
        if i == excluir or contagem[i] >= limite_maximo:
            continue
        d = haversine_metros(p, c)
        if melhor == -1 or d < melhor_dist:
            melhor, melhor_dist = i, d
    return melhor


def _rebalancear(pontos: list[_PontoCluster], atribuicao: list[int], centroides: list[GeoPonto]) -> None:
    n, k = len(pontos), len(centroides)
    if k == 0:
        return

    tamanho_medio = n / k
    limite_maximo = max(1, int(tamanho_medio * TOLERANCIA_BALANCEAMENTO))

    contagem = [0] * k
    for c in atribuicao:
        contagem[c] += 1

    for cluster in range(k):
        while contagem[cluster] > limite_maximo:
            idx_mais_distante, dist_max = -1, -1.0
            for i, p in enumerate(pontos):
                if atribuicao[i] != cluster:
                    continue
                d = haversine_metros(p.geo, centroides[cluster])
                if d > dist_max:
                    idx_mais_distante, dist_max = i, d
            if idx_mais_distante == -1:
                break

            destino = _cluster_vizinho_com_folga(pontos[idx_mais_distante].geo, centroides, contagem, limite_maximo, cluster)
            if destino == -1:
                break

            atribuicao[idx_mais_distante] = destino
            contagem[cluster] -= 1
            contagem[destino] += 1

