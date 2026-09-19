"""TSP heurístico da carteira de um fiscal — porta fiel de
internal/service/routing_service.go: matriz de distância completa (Haversine)
+ nearest-neighbor + 2-opt, tratado como caminho aberto (o fiscal não volta
ao primeiro condomínio).

A matriz n×n e os vetores de controle do solver (visitado, ordem) usam listas
nativas de propósito: não são o "Vetor" do syllabus (cadastro/carteira do
domínio) — são estado escalar de um algoritmo numérico, equivalentes às
slices que o próprio Go já usa aqui.
"""

import math
from datetime import datetime
from typing import Optional

from backend.domain.rota import GeoPonto, Rota, RotaParada

RAIO_TERRA_METROS = 6_371_000.0


def _graus_para_rad(graus: float) -> float:
    return graus * math.pi / 180


def haversine_metros(a: GeoPonto, b: GeoPonto) -> float:
    lat1, lat2 = _graus_para_rad(a.latitude), _graus_para_rad(b.latitude)
    d_lat = _graus_para_rad(b.latitude - a.latitude)
    d_lng = _graus_para_rad(b.longitude - a.longitude)

    sin_d_lat_2 = math.sin(d_lat / 2)
    sin_d_lng_2 = math.sin(d_lng / 2)

    h = sin_d_lat_2**2 + math.cos(lat1) * math.cos(lat2) * sin_d_lng_2**2
    c = 2 * math.atan2(math.sqrt(h), math.sqrt(max(0.0, 1 - h)))
    return RAIO_TERRA_METROS * c


def _construir_matriz(pontos: list[GeoPonto]) -> list[list[float]]:
    n = len(pontos)
    matriz = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                matriz[i][j] = haversine_metros(pontos[i], pontos[j])
    return matriz


def _nearest_neighbor(matriz: list[list[float]], n: int, inicio: int) -> list[int]:
    visitado = [False] * n
    ordem = [inicio]
    visitado[inicio] = True
    atual = inicio

    while len(ordem) < n:
        melhor, melhor_dist = -1, math.inf
        for candidato in range(n):
            if visitado[candidato]:
                continue
            if matriz[atual][candidato] < melhor_dist:
                melhor, melhor_dist = candidato, matriz[atual][candidato]
        visitado[melhor] = True
        ordem.append(melhor)
        atual = melhor
    return ordem


def _reverter(ordem: list[int], i: int, j: int) -> None:
    while i < j:
        ordem[i], ordem[j] = ordem[j], ordem[i]
        i += 1
        j -= 1


def _two_opt(ordem: list[int], matriz: list[list[float]]) -> list[int]:
    n = len(ordem)
    if n < 4:
        return ordem

    melhorou = True
    while melhorou:
        melhorou = False
        for i in range(n - 2):
            a, b = ordem[i], ordem[i + 1]
            for j in range(i + 2, n):
                c = ordem[j]
                if j == n - 1:
                    custo_antes = matriz[a][b]
                    custo_depois = matriz[a][c]
                else:
                    depois = ordem[j + 1]
                    custo_antes = matriz[a][b] + matriz[c][depois]
                    custo_depois = matriz[a][c] + matriz[b][depois]

                if custo_depois < custo_antes - 1e-9:
                    _reverter(ordem, i + 1, j)
                    melhorou = True
                    b = ordem[i + 1]
    return ordem


def _distancia_da_rota(ordem: list[int], matriz: list[list[float]]) -> float:
    return sum(matriz[ordem[i]][ordem[i + 1]] for i in range(len(ordem) - 1))


class RoutingService:
    def __init__(self, store):
        self._store = store

    def otimizar_ordem_de(self, pontos: list[GeoPonto], inicio: int = 0) -> tuple[list[int], float]:
        n = len(pontos)
        if n <= 1:
            return list(range(n)), 0.0
        if inicio < 0 or inicio >= n:
            inicio = 0

        matriz = _construir_matriz(pontos)
        ordem = _nearest_neighbor(matriz, n, inicio)
        ordem = _two_opt(ordem, matriz)
        distancia_total = _distancia_da_rota(ordem, matriz)
        return ordem, distancia_total

    def gerar_rota_do_dia(self, fiscal_id: str, data: Optional[datetime] = None) -> Rota:
        data = data or datetime.utcnow()
        condominios = self._store.listar_por_fiscal(fiscal_id)

        pontos_validos = []
        condominios_validos = []
        for c in condominios:
            if not c.tem_localizacao():
                continue
            pontos_validos.append(GeoPonto(id=c.id, latitude=c.latitude, longitude=c.longitude))
            condominios_validos.append(c)

        ordem_idx, distancia_total = self.otimizar_ordem_de(pontos_validos, 0)

        rota = Rota(fiscal_id=fiscal_id, data_rota=data, distancia_total_metros=distancia_total)
        for posicao, idx in enumerate(ordem_idx):
            rota.paradas.append(
                RotaParada(
                    condominio_id=condominios_validos[idx].id,
                    condominio_nome=condominios_validos[idx].nome,
                    ordem=posicao + 1,
                    latitude=pontos_validos[idx].latitude,
                    longitude=pontos_validos[idx].longitude,
                )
            )

        return self._store.salvar_rota(rota)
