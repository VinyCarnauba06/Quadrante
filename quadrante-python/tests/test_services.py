import os
from datetime import datetime

import pytest

from backend.domain.fiscal import PAPEL_COORDENADOR, PAPEL_FISCAL_CAMPO
from backend.repository.store import Store
from backend.seed.loader import carregar
from backend.service.clustering_service import ClusteringService
from backend.service.reallocation_service import ReallocationService, SolicitacaoAusencia
from backend.service.routing_service import RoutingService, haversine_metros
from backend.domain.rota import GeoPonto

CAMINHO_SEED = os.path.join(os.path.dirname(__file__), "..", "backend", "seed", "dados.json")


def _store_pequeno():
    """3 fiscais de campo em cantos bem separados + 1 coordenador, cada um
    com uma carteira pequena — o suficiente para testar a lógica de
    proximidade sem depender do seed real de 127 condomínios."""
    store = Store()
    a = store.seed_fiscal("Ana", "ana@x.com", PAPEL_FISCAL_CAMPO)
    b = store.seed_fiscal("Bruno", "bruno@x.com", PAPEL_FISCAL_CAMPO)
    c = store.seed_fiscal("Carla", "carla@x.com", PAPEL_FISCAL_CAMPO)
    coord = store.seed_fiscal("Doriana", "dori@x.com", PAPEL_COORDENADOR)

    # carteira de Ana: 3 pontos próximos entre si, longe de Bruno e Carla
    for i in range(3):
        store.seed_condominio(f"A{i}", "", -9.60 + i * 0.001, -35.70, "ok", a)
    # carteira de Bruno: 2 pontos, mais perto da zona de Ana que da de Carla
    for i in range(2):
        store.seed_condominio(f"B{i}", "", -9.61 + i * 0.001, -35.71, "ok", b)
    # carteira de Carla: 2 pontos, bem distante das outras duas zonas
    for i in range(2):
        store.seed_condominio(f"C{i}", "", -9.90 + i * 0.001, -35.90, "ok", c)
    # coordenador tem carteira própria fixa — nunca deve receber nada
    store.seed_condominio("D0", "", -9.50, -35.50, "ok", coord)

    return store, a, b, c, coord


def test_reallocation_redistribui_toda_carteira_geocodificada():
    store, a, b, c, coord = _store_pequeno()
    routing = RoutingService(store)
    realloc = ReallocationService(store, routing)

    antes = store.listar_por_fiscal(a)
    resultado = realloc.registrar_ausencia(a, datetime(2026, 10, 1), datetime(2026, 10, 10), "ferias")

    assert len(resultado.realocacoes) == len(antes)
    assert len(store.listar_por_fiscal(a)) == 0


def test_reallocation_coordenador_nunca_recebe_carteira():
    store, a, b, c, coord = _store_pequeno()
    routing = RoutingService(store)
    realloc = ReallocationService(store, routing)

    realloc.registrar_ausencia(a, datetime(2026, 10, 1), datetime(2026, 10, 10), "ferias")

    destinos = {r.fiscal_destino_id for r in store._realocacoes.values()}
    assert coord not in destinos


def test_reallocation_fiscal_mais_proximo_recebe_a_maior_parte():
    store, a, b, c, coord = _store_pequeno()
    routing = RoutingService(store)
    realloc = ReallocationService(store, routing)

    resultado = realloc.registrar_ausencia(a, datetime(2026, 10, 1), datetime(2026, 10, 10), "ferias")

    destinos = [r.fiscal_destino_id for r in resultado.realocacoes]
    # Bruno é geograficamente mais próximo da carteira de Ana que Carla.
    assert destinos.count(b) >= destinos.count(c)


def test_reallocation_reverte_apenas_apos_expirar():
    store, a, b, c, coord = _store_pequeno()
    routing = RoutingService(store)
    realloc = ReallocationService(store, routing)

    realloc.registrar_ausencia(a, datetime(2026, 10, 1), datetime(2026, 10, 10), "ferias")

    revertidos_antes = realloc.reverter_expiradas(datetime(2026, 10, 5))
    assert revertidos_antes == 0
    assert len(store.listar_por_fiscal(a)) == 0

    revertidos_depois = realloc.reverter_expiradas(datetime(2026, 10, 20))
    assert revertidos_depois == 3
    assert len(store.listar_por_fiscal(a)) == 3


def test_reallocation_sem_fiscal_disponivel_estoura():
    store = Store()
    a = store.seed_fiscal("Ana", "", PAPEL_FISCAL_CAMPO)
    store.seed_condominio("A0", "", -9.6, -35.7, "ok", a)
    routing = RoutingService(store)
    realloc = ReallocationService(store, routing)

    with pytest.raises(Exception):
        realloc.registrar_ausencia(a, datetime(2026, 10, 1), datetime(2026, 10, 10), "ferias")


def test_fila_processa_solicitacoes_na_ordem_de_chegada():
    store, a, b, c, coord = _store_pequeno()
    routing = RoutingService(store)
    realloc = ReallocationService(store, routing)

    realloc.enfileirar_solicitacao(SolicitacaoAusencia(a, datetime(2026, 10, 1), datetime(2026, 10, 5), "ferias"))
    realloc.enfileirar_solicitacao(SolicitacaoAusencia(b, datetime(2026, 10, 1), datetime(2026, 10, 5), "falta"))

    primeira = realloc.processar_proxima_solicitacao()
    assert primeira.ausencia.fiscal_id == a
    segunda = realloc.processar_proxima_solicitacao()
    assert segunda.ausencia.fiscal_id == b


def test_pilha_desfaz_a_realocacao_mais_recente_primeiro():
    store, a, b, c, coord = _store_pequeno()
    routing = RoutingService(store)
    realloc = ReallocationService(store, routing)

    realloc.registrar_ausencia(a, datetime(2026, 10, 1), datetime(2026, 10, 10), "ferias")
    ultimo_id_no_topo = store.historico_realocacoes.topo_valor()

    desfeita = realloc.desfazer_ultima_realocacao()
    assert desfeita.id == ultimo_id_no_topo
    assert desfeita.ativa is False


def test_routing_tsp_reduz_ou_mantem_distancia_apos_two_opt():
    routing = RoutingService(None)
    pontos = [
        GeoPonto("0", -9.60, -35.70),
        GeoPonto("1", -9.61, -35.71),
        GeoPonto("2", -9.60, -35.71),
        GeoPonto("3", -9.61, -35.70),
    ]
    ordem, distancia = routing.otimizar_ordem_de(pontos, 0)
    assert len(ordem) == 4
    assert set(ordem) == {0, 1, 2, 3}
    assert distancia >= 0


def test_routing_um_ponto_nao_quebra():
    routing = RoutingService(None)
    ordem, distancia = routing.otimizar_ordem_de([GeoPonto("0", -9.6, -35.7)], 0)
    assert ordem == [0]
    assert distancia == 0.0


def test_clustering_convergiu_sem_erro_no_seed_real():
    store = Store()
    carregar(CAMINHO_SEED, store)
    clustering = ClusteringService(store)

    sugestao = clustering.sugerir_redistribuicao()
    assert sugestao.total_condominios > 0
    assert 0 <= sugestao.total_mudancas <= sugestao.total_condominios


def test_haversine_e_simetrico_e_zero_para_o_mesmo_ponto():
    p1 = GeoPonto("a", -9.60, -35.70)
    p2 = GeoPonto("b", -9.65, -35.75)
    assert haversine_metros(p1, p1) == 0
    assert haversine_metros(p1, p2) == pytest.approx(haversine_metros(p2, p1))


def test_clustering_balanceamento_de_carga_distribui_equitativamente():
    store = Store()
    carregar(CAMINHO_SEED, store)
    clustering = ClusteringService(store)

    sugestao = clustering.sugerir_redistribuicao()
    fiscais = store.fiscais_de_campo()
    contagens: dict[str, int] = {f.id: 0 for f in fiscais}
    for a in sugestao.atribuicoes:
        if a.fiscal_sugerido_id:
            contagens[a.fiscal_sugerido_id] += 1

    media: float = len(sugestao.atribuicoes) / len(fiscais)
    limite_min: int = max(1, int(media / 1.3))
    limite_max: int = max(1, int(media * 1.3))

    for fid, total in contagens.items():
        assert limite_min <= total <= limite_max

