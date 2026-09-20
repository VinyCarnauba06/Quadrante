import os
import sys
import time
from datetime import datetime, timezone

from backend.repository.store import Store
from backend.seed.loader import carregar
from backend.service.clustering_service import ClusteringService
from backend.service.routing_service import RoutingService

CAMINHO_SEED: str = os.path.join(os.path.dirname(__file__), "backend", "seed", "dados.json")


def executar_benchmarks() -> int:
    store: Store = Store()
    carregar(CAMINHO_SEED, store)
    routing: RoutingService = RoutingService(store)
    clustering: ClusteringService = ClusteringService(store)

    print("=" * 64)
    print("        QUADRANTE — MEDIÇÃO DE TEMPO DE CÁLCULO E BENCHMARK")
    print("=" * 64)

    fiscais = store.fiscais_de_campo()
    sucesso: bool = True

    print("\n[1] Roteirização TSP (Vizinho Mais Próximo + 2-opt, Haversine):")
    for f in fiscais:
        inicio: float = time.perf_counter()
        rota = routing.gerar_rota_do_dia(f.id, datetime.now(timezone.utc))
        duracao_ms: float = (time.perf_counter() - inicio) * 1000.0
        distancia_km: float = rota.distancia_total_metros / 1000.0
        paradas_qtd: int = len(rota.paradas)
        status_txt: str = "OK" if duracao_ms < 50.0 else "LENTO"
        if duracao_ms >= 50.0:
            sucesso = False
        print(f"  - Fiscal {f.nome} ({paradas_qtd} visitas, {distancia_km:.2f} km): {duracao_ms:.2f} ms [{status_txt}]")

    print("\n[2] Redistribuição Territorial (Lloyd + Rebalanceamento de Carga):")
    inicio_cluster: float = time.perf_counter()
    sugestao = clustering.sugerir_redistribuicao()
    duracao_cluster_ms: float = (time.perf_counter() - inicio_cluster) * 1000.0
    status_cluster: str = "OK" if duracao_cluster_ms < 100.0 else "LENTO"
    if duracao_cluster_ms >= 100.0:
        sucesso = False
    print(f"  - Total de condomínios avaliados: {sugestao.total_condominios}")
    print(f"  - Total de trocas sugeridas: {sugestao.total_mudancas}")
    print(f"  - Tempo de cálculo: {duracao_cluster_ms:.2f} ms (limite: 100.00 ms) [{status_cluster}]")

    print("\n" + "=" * 64)
    if sucesso:
        print("  Todos os cálculos executaram abaixo dos limites de latência!")
        print("=" * 64)
        return 0
    else:
        print("  Atenção: Houve cálculo que excedeu o tempo esperado.")
        print("=" * 64)
        return 1


if __name__ == "__main__":
    sys.exit(executar_benchmarks())
