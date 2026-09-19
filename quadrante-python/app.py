"""Entrypoint Flask do Quadrante — só monta rotas. Toda a lógica de domínio,
estruturas de dados e algoritmos vive em backend/; toda a apresentação
(HTML/CSS/JS) vive em frontend/. Nenhum dos dois conhece o outro: backend/
não importa nada de frontend/, e app.py é a única peça que junta os dois.
"""

import os
import threading
from datetime import datetime

from flask import Flask, jsonify, request, render_template

from backend.domain.clustering import AtribuicaoSugerida
from backend.repository.store import Store
from backend.seed.loader import carregar
from backend.service.clustering_service import ClusteringService
from backend.service.reallocation_service import ReallocationService, SolicitacaoAusencia
from backend.service.routing_service import RoutingService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_SEED = os.path.join(BASE_DIR, "backend", "seed", "dados.json")

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "frontend", "templates"),
    static_folder=os.path.join(BASE_DIR, "frontend", "static"),
)

_lock = threading.Lock()
_estado = {}


def _inicializar_estado():
    store = Store()
    carregar(CAMINHO_SEED, store)
    routing = RoutingService(store)
    clustering = ClusteringService(store)
    realloc = ReallocationService(store, routing)
    return {"store": store, "routing": routing, "clustering": clustering, "realloc": realloc}


_estado.update(_inicializar_estado())


def _fiscal_para_json(f, carga_por_fiscal):
    return {
        "id": f.id,
        "nome": f.nome,
        "papel": f.papel,
        "ativo": f.ativo,
        "qtd_condominios": carga_por_fiscal.get(f.id, 0),
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/fiscais")
def listar_fiscais():
    store = _estado["store"]
    carga = store.carga_por_fiscal()
    fiscais = sorted(store.listar(somente_ativos=True), key=lambda f: f.id)
    return jsonify([_fiscal_para_json(f, carga) for f in fiscais])


@app.get("/api/fiscais/<fiscal_id>/rota")
def gerar_rota(fiscal_id):
    with _lock:
        routing = _estado["routing"]
        rota = routing.gerar_rota_do_dia(fiscal_id, datetime.utcnow())
    return jsonify({
        "fiscal_id": fiscal_id,
        "distancia_total_km": round(rota.distancia_total_metros / 1000, 2),
        "paradas": [
            {
                "ordem": p.ordem,
                "condominio_id": p.condominio_id,
                "condominio_nome": p.condominio_nome,
                "latitude": p.latitude,
                "longitude": p.longitude,
            }
            for p in sorted(rota.paradas, key=lambda x: x.ordem)
        ],
    })


@app.get("/api/mapa-geral")
def mapa_geral():
    store = _estado["store"]
    fiscais = []
    for f in sorted(store.listar(somente_ativos=True), key=lambda x: x.id):
        condominios = [c for c in store.listar_por_fiscal(f.id) if c.tem_localizacao()]
        fiscais.append({
            "id": f.id,
            "nome": f.nome,
            "papel": f.papel,
            "condominios": [
                {"id": c.id, "nome": c.nome, "latitude": c.latitude, "longitude": c.longitude}
                for c in condominios
            ],
        })
    return jsonify({"fiscais": fiscais})


@app.get("/api/clustering/sugestao")
def sugestao_clustering():
    clustering = _estado["clustering"]
    try:
        sugestao = clustering.sugerir_redistribuicao()
    except Exception as erro:
        return jsonify({"erro": str(erro)}), 400

    por_fiscal = {}
    for a in sugestao.atribuicoes:
        por_fiscal[a.fiscal_sugerido_nome] = por_fiscal.get(a.fiscal_sugerido_nome, 0) + 1

    mudancas = [
        {
            "condominio_id": a.condominio_id,
            "condominio_nome": a.condominio_nome,
            "fiscal_atual_nome": a.fiscal_atual_nome,
            "fiscal_sugerido_id": a.fiscal_sugerido_id,
            "fiscal_sugerido_nome": a.fiscal_sugerido_nome,
        }
        for a in sugestao.atribuicoes if a.mudou
    ]

    return jsonify({
        "total_condominios": sugestao.total_condominios,
        "total_mudancas": sugestao.total_mudancas,
        "tamanho_por_zona": por_fiscal,
        "mudancas": mudancas,
        "_atribuicoes_completas": [
            {
                "condominio_id": a.condominio_id,
                "condominio_nome": a.condominio_nome,
                "fiscal_atual_id": a.fiscal_atual_id,
                "fiscal_atual_nome": a.fiscal_atual_nome,
                "fiscal_sugerido_id": a.fiscal_sugerido_id,
                "fiscal_sugerido_nome": a.fiscal_sugerido_nome,
                "mudou": a.mudou,
            }
            for a in sugestao.atribuicoes
        ],
    })


@app.post("/api/clustering/aplicar")
def aplicar_clustering():
    clustering = _estado["clustering"]
    payload = request.get_json(force=True) or {}
    atribuicoes = [
        AtribuicaoSugerida(
            condominio_id=item["condominio_id"],
            condominio_nome=item.get("condominio_nome", ""),
            fiscal_atual_id=item.get("fiscal_atual_id", ""),
            fiscal_atual_nome=item.get("fiscal_atual_nome", ""),
            fiscal_sugerido_id=item["fiscal_sugerido_id"],
            fiscal_sugerido_nome=item.get("fiscal_sugerido_nome", ""),
            mudou=item.get("mudou", True),
        )
        for item in payload.get("atribuicoes", [])
    ]
    with _lock:
        aplicadas = clustering.aplicar_redistribuicao(atribuicoes)
    return jsonify({"aplicadas": aplicadas})


@app.post("/api/ausencias")
def registrar_solicitacao_ausencia():
    payload = request.get_json(force=True) or {}
    realloc = _estado["realloc"]
    try:
        solicitacao = SolicitacaoAusencia(
            fiscal_id=payload["fiscal_id"],
            data_inicio=datetime.fromisoformat(payload["data_inicio"]),
            data_fim=datetime.fromisoformat(payload["data_fim"]),
            motivo=payload.get("motivo", "outro"),
            observacao=payload.get("observacao", ""),
        )
    except (KeyError, ValueError) as erro:
        return jsonify({"erro": f"payload inválido: {erro}"}), 400

    with _lock:
        tamanho_fila = realloc.enfileirar_solicitacao(solicitacao)
    return jsonify({"enfileirada": True, "tamanho_fila": tamanho_fila})


@app.get("/api/ausencias/fila")
def ver_fila():
    store = _estado["store"]
    itens = store.fila_solicitacoes_ausencia.para_lista()  # frente -> fim
    resultado = []
    for s in itens:
        try:
            fiscal_nome = store.buscar_fiscal(s.fiscal_id).nome
        except Exception:
            fiscal_nome = s.fiscal_id
        resultado.append({
            "fiscal_id": s.fiscal_id,
            "fiscal_nome": fiscal_nome,
            "data_inicio": s.data_inicio.isoformat(),
            "data_fim": s.data_fim.isoformat(),
            "motivo": s.motivo,
        })
    return jsonify(resultado)


@app.post("/api/ausencias/processar-proxima")
def processar_proxima():
    realloc = _estado["realloc"]
    with _lock:
        if len(_estado["store"].fila_solicitacoes_ausencia) == 0:
            return jsonify({"erro": "fila vazia"}), 400
        try:
            resultado = realloc.processar_proxima_solicitacao()
        except Exception as erro:
            return jsonify({"erro": str(erro)}), 400

    return jsonify({
        "fiscal_id": resultado.ausencia.fiscal_id,
        "ausencia_id": resultado.ausencia.id,
        "qtd_realocacoes": len(resultado.realocacoes),
        "realocacoes": [
            {"condominio_id": r.condominio_id, "destino_id": r.fiscal_destino_id, "distancia_m": round(r.distancia_metros, 1)}
            for r in resultado.realocacoes
        ],
    })


@app.post("/api/realocacoes/reverter-expiradas")
def reverter_expiradas():
    payload = request.get_json(force=True) or {}
    hoje = datetime.fromisoformat(payload["hoje"]) if payload.get("hoje") else datetime.utcnow()
    realloc = _estado["realloc"]
    with _lock:
        revertidos = realloc.reverter_expiradas(hoje)
    return jsonify({"revertidos": revertidos})


@app.post("/api/realocacoes/desfazer")
def desfazer():
    realloc = _estado["realloc"]
    with _lock:
        desfeita = realloc.desfazer_ultima_realocacao()
    if desfeita is None:
        return jsonify({"erro": "nada para desfazer"}), 400
    return jsonify({
        "condominio_id": desfeita.condominio_id,
        "voltou_para": desfeita.fiscal_origem_id,
        "saiu_de": desfeita.fiscal_destino_id,
    })


@app.get("/api/historico")
def historico():
    store = _estado["store"]
    ids = store.historico_realocacoes.para_lista()  # topo -> base
    itens = []
    for rid in ids:
        r = store.buscar_realocacao(rid)
        if r is None:
            continue

        condominio = store.buscar_condominio(r.condominio_id)
        try:
            fiscal_de_nome = store.buscar_fiscal(r.fiscal_origem_id).nome
        except Exception:
            fiscal_de_nome = r.fiscal_origem_id
        try:
            fiscal_para_nome = store.buscar_fiscal(r.fiscal_destino_id).nome
        except Exception:
            fiscal_para_nome = r.fiscal_destino_id

        itens.append({
            "id": r.id,
            "condominio_id": r.condominio_id,
            "condominio_nome": condominio.nome if condominio else r.condominio_id,
            "de": r.fiscal_origem_id,
            "de_nome": fiscal_de_nome,
            "para": r.fiscal_destino_id,
            "para_nome": fiscal_para_nome,
            "ativa": r.ativa,
            "distancia_m": round(r.distancia_metros, 1),
        })
    return jsonify(itens)


@app.post("/api/reset")
def resetar():
    with _lock:
        _estado.update(_inicializar_estado())
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
