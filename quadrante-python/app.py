"""Entrypoint Flask do Quadrante — só monta rotas. Toda a lógica de domínio,
estruturas de dados e algoritmos vive em backend/; toda a apresentação
(HTML/CSS/JS) vive em frontend/. Nenhum dos dois conhece o outro: backend/
não importa nada de frontend/, e app.py é a única peça que junta os dois.
"""

import os
import threading
from datetime import datetime

from typing import Optional

from flask import Flask, jsonify, request, render_template, session, Response

from backend.config import carregar_configuracao
from backend.domain.clustering import AtribuicaoSugerida
from backend.domain.fiscal import PAPEL_ADMIN, PAPEL_OPERADOR, PAPEL_FISCAL_CAMPO, PAPEL_COORDENADOR, Fiscal
from backend.infra.geoapify import GeoapifyGeocodificador
from backend.repository.store import Store
from backend.seed.loader import carregar
from backend.service.auth_service import AuthService, CredenciaisInvalidasError, UsuarioInativoError
from backend.service.cadastro_service import CadastroService, DadosInvalidosError, SemFiscalParaCadastroError
from backend.service.clustering_service import ClusteringService
from backend.service.geocoding_service import (
    GeocodificacaoFalhouError,
    GeocodificacaoIndisponivelError,
    GeocodificadorAusente,
)
from backend.service.reallocation_service import ReallocationService, SolicitacaoAusencia
from backend.service.routing_service import RoutingService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_SEED = os.path.join(BASE_DIR, "backend", "seed", "dados.json")
config = carregar_configuracao(BASE_DIR)
geocodificador = GeoapifyGeocodificador(config.geoapify_chave) if config.geoapify_chave else GeocodificadorAusente()

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "frontend", "templates"),
    static_folder=os.path.join(BASE_DIR, "frontend", "static"),
)
app.secret_key = os.environ.get("QUADRANTE_SECRET_KEY", "quadrante-segredo-sessao-2026")
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

_lock = threading.Lock()
_estado = {}


def _inicializar_estado():
    store = Store()
    carregar(CAMINHO_SEED, store)
    routing = RoutingService(store)
    clustering = ClusteringService(store)
    realloc = ReallocationService(store, routing)
    cadastro = CadastroService(store, geocodificador)
    auth = AuthService(store)
    return {
        "store": store,
        "routing": routing,
        "clustering": clustering,
        "realloc": realloc,
        "cadastro": cadastro,
        "auth": auth,
    }


_estado.update(_inicializar_estado())


def _fiscal_para_json(f, carga_por_fiscal):
    return {
        "id": f.id,
        "nome": f.nome,
        "papel": f.papel,
        "ativo": f.ativo,
        "qtd_condominios": carga_por_fiscal.get(f.id, 0),
    }


def _usuario_atual() -> Optional[Fiscal]:
    fiscal_id = session.get("fiscal_id")
    if not fiscal_id:
        return None
    store = _estado["store"]
    try:
        return store.buscar_fiscal(fiscal_id)
    except Exception:
        return None


def _exigir_papeis(*papeis_permitidos: str) -> tuple[bool, Optional[tuple]]:
    usuario = _usuario_atual()
    if usuario is None:
        return True, None
    if usuario.is_admin():
        return True, None
    if usuario.papel not in papeis_permitidos:
        return False, (jsonify({"erro": "Acesso não autorizado para o seu perfil."}), 403)
    return True, None


@app.get("/api/auth/me")
def auth_me():
    usuario = _usuario_atual()
    if usuario is None:
        return jsonify({"autenticado": False, "usuario": None})
    return jsonify({
        "autenticado": True,
        "usuario": {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "papel": usuario.papel,
        },
    })


@app.get("/api/auth/contas-demo")
def auth_contas_demo():
    store = _estado["store"]
    todos = store.listar(somente_ativos=True)
    contas = []
    for f in todos:
        if f.papel in (PAPEL_ADMIN, PAPEL_OPERADOR, PAPEL_FISCAL_CAMPO):
            contas.append({
                "id": f.id,
                "nome": f.nome,
                "email": f.email,
                "papel": f.papel,
            })
    return jsonify(contas)


@app.post("/api/auth/login")
def auth_login():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "")
    senha = payload.get("senha", "")
    auth = _estado["auth"]
    try:
        fiscal = auth.autenticar(email, senha)
    except CredenciaisInvalidasError as erro:
        return jsonify({"erro": str(erro)}), 401
    except UsuarioInativoError as erro:
        return jsonify({"erro": str(erro)}), 403

    session["fiscal_id"] = fiscal.id
    return jsonify({
        "autenticado": True,
        "usuario": {
            "id": fiscal.id,
            "nome": fiscal.nome,
            "email": fiscal.email,
            "papel": fiscal.papel,
        },
    })


@app.post("/api/auth/logout")
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/")
def index():
    return render_template("index.html", geoapify_chave=config.geoapify_chave)


@app.get("/login")
def login_view():
    session.clear()
    return render_template("index.html", geoapify_chave=config.geoapify_chave)


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status=204)


@app.get("/.well-known/<path:subpath>")
def well_known(subpath: str) -> Response:
    return Response(status=204)


@app.get("/api/geocodificar")
def geocodificar():
    cadastro = _estado["cadastro"]
    try:
        candidatos = cadastro.localizar(request.args.get("q", ""))
    except DadosInvalidosError as erro:
        return jsonify({"erro": str(erro)}), 400
    except GeocodificacaoIndisponivelError as erro:
        return jsonify({"erro": str(erro)}), 503
    except GeocodificacaoFalhouError as erro:
        return jsonify({"erro": str(erro)}), 502

    return jsonify({
        "candidatos": [
            {
                "endereco": c.resultado.endereco,
                "bairro": c.resultado.bairro,
                "latitude": c.resultado.latitude,
                "longitude": c.resultado.longitude,
                "confianca": c.resultado.confianca,
                "fiscal_sugerido_id": c.destino.fiscal.id if c.destino else None,
                "fiscal_sugerido_nome": c.destino.fiscal.nome if c.destino else None,
                "distancia_m": round(c.destino.distancia_metros, 1) if c.destino else None,
            }
            for c in candidatos
        ]
    })


@app.post("/api/condominios")
def cadastrar_condominio():
    autorizado, erro_resp = _exigir_papeis(PAPEL_ADMIN, PAPEL_OPERADOR)
    if not autorizado:
        return erro_resp

    payload = request.get_json(silent=True) or {}
    cadastro = _estado["cadastro"]
    try:
        with _lock:
            condominio, destino = cadastro.cadastrar(
                payload.get("nome"),
                payload.get("endereco"),
                payload.get("latitude"),
                payload.get("longitude"),
            )
    except DadosInvalidosError as erro:
        return jsonify({"erro": str(erro)}), 400
    except SemFiscalParaCadastroError as erro:
        return jsonify({"erro": str(erro)}), 409

    return jsonify({
        "id": condominio.id,
        "nome": condominio.nome,
        "endereco": condominio.endereco_formatado,
        "latitude": condominio.latitude,
        "longitude": condominio.longitude,
        "fiscal_id": destino.fiscal.id,
        "fiscal_nome": destino.fiscal.nome,
        "distancia_m": round(destino.distancia_metros, 1),
    }), 201


@app.get("/api/fiscais")
def listar_fiscais():
    usuario = _usuario_atual()
    store = _estado["store"]
    carga = store.carga_por_fiscal()
    if usuario and usuario.is_fiscal_campo():
        fiscais = [store.buscar_fiscal(usuario.id)]
    else:
        fiscais = sorted(store.fiscais_de_campo(somente_ativos=True), key=lambda f: f.id)
    return jsonify([_fiscal_para_json(f, carga) for f in fiscais])


@app.get("/api/fiscais/<fiscal_id>/rota")
def gerar_rota(fiscal_id):
    usuario = _usuario_atual()
    if usuario and usuario.is_fiscal_campo() and usuario.id != fiscal_id:
        return jsonify({"erro": "Acesso não autorizado à rota de outro fiscal."}), 403

    with _lock:
        routing = _estado["routing"]
        rota = routing.gerar_rota_do_dia(fiscal_id, datetime.utcnow())
    store = _estado["store"]

    def endereco_de(condominio_id):
        condominio = store.buscar_condominio(condominio_id)
        return condominio.endereco_formatado if condominio else ""

    return jsonify({
        "fiscal_id": fiscal_id,
        "distancia_total_km": round(rota.distancia_total_metros / 1000, 2),
        "paradas": [
            {
                "ordem": p.ordem,
                "condominio_id": p.condominio_id,
                "condominio_nome": p.condominio_nome,
                "endereco": endereco_de(p.condominio_id),
                "latitude": p.latitude,
                "longitude": p.longitude,
            }
            for p in sorted(rota.paradas, key=lambda x: x.ordem)
        ],
    })


@app.get("/api/mapa-geral")
def mapa_geral():
    usuario = _usuario_atual()
    store = _estado["store"]
    fiscais = []
    lista_fiscais = sorted(store.fiscais_de_campo(somente_ativos=True), key=lambda x: x.id)
    if usuario and usuario.is_fiscal_campo():
        lista_fiscais = [f for f in lista_fiscais if f.id == usuario.id]

    for f in lista_fiscais:
        condominios = [c for c in store.listar_por_fiscal(f.id) if c.tem_localizacao()]
        fiscais.append({
            "id": f.id,
            "nome": f.nome,
            "papel": f.papel,
            "condominios": [
                {
                    "id": c.id,
                    "nome": c.nome,
                    "endereco": c.endereco_formatado,
                    "latitude": c.latitude,
                    "longitude": c.longitude,
                }
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
    autorizado, erro_resp = _exigir_papeis(PAPEL_ADMIN)
    if not autorizado:
        return erro_resp

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
    autorizado, erro_resp = _exigir_papeis(PAPEL_ADMIN, PAPEL_OPERADOR)
    if not autorizado:
        return erro_resp

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
    autorizado, erro_resp = _exigir_papeis(PAPEL_ADMIN, PAPEL_OPERADOR)
    if not autorizado:
        return erro_resp

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
    autorizado, erro_resp = _exigir_papeis(PAPEL_ADMIN, PAPEL_OPERADOR)
    if not autorizado:
        return erro_resp

    payload = request.get_json(force=True) or {}
    hoje = datetime.fromisoformat(payload["hoje"]) if payload.get("hoje") else datetime.utcnow()
    realloc = _estado["realloc"]
    with _lock:
        revertidos = realloc.reverter_expiradas(hoje)
    return jsonify({"revertidos": revertidos})


@app.post("/api/realocacoes/desfazer")
def desfazer():
    autorizado, erro_resp = _exigir_papeis(PAPEL_ADMIN)
    if not autorizado:
        return erro_resp

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


@app.get("/api/estruturas/raio-x")
def estruturas_raio_x():
    store = _estado["store"]
    fid = request.args.get("fiscal_id")

    fiscais_dados: list[dict] = []
    for f in store.fiscais:
        fiscais_dados.append({
            "id": f.id,
            "nome": f.nome,
            "papel": f.papel,
            "ativo": f.ativo,
        })
    vetor_info = {
        "classe": "Vetor",
        "tamanho": len(store.fiscais),
        "capacidade": store.fiscais.capacidade,
        "complexidade": "O(1) amortizado inserção, O(1) acesso indexado",
        "elementos": fiscais_dados,
    }

    if not fid:
        for f in store.fiscais:
            if f.papel == PAPEL_FISCAL_CAMPO and f.ativo:
                fid = f.id
                break

    carteira = store._carteira_de(fid) if fid else None
    nos_encadeados: list[dict] = []
    if carteira:
        for cond in carteira:
            nos_encadeados.append({
                "id": cond.id,
                "nome": cond.nome,
                "endereco": cond.endereco_formatado,
            })

    fiscal_alvo = None
    if fid:
        try:
            f_encontrado = store.buscar_fiscal(fid)
            fiscal_alvo = {"id": f_encontrado.id, "nome": f_encontrado.nome}
        except Exception:
            fiscal_alvo = {"id": fid, "nome": fid}

    lista_info = {
        "classe": "ListaEncadeada",
        "fiscal": fiscal_alvo,
        "tamanho": len(carteira) if carteira else 0,
        "complexidade": "O(1) inserção/remoção por ponteiros sem deslocar memória",
        "elementos": nos_encadeados,
    }

    fila_solicitacoes = store.fila_solicitacoes_ausencia.para_lista()
    solicitacoes_dados: list[dict] = []
    for s in fila_solicitacoes:
        f_nome = s.fiscal_id
        try:
            f_obj = store.buscar_fiscal(s.fiscal_id)
            f_nome = f_obj.nome
        except Exception:
            pass
        solicitacoes_dados.append({
            "fiscal_id": s.fiscal_id,
            "fiscal_nome": f_nome,
            "motivo": s.motivo,
            "data_inicio": s.data_inicio.isoformat() if s.data_inicio else "",
            "data_fim": s.data_fim.isoformat() if s.data_fim else "",
        })
    fila_info = {
        "classe": "Fila",
        "disciplina": "FIFO (First In, First Out)",
        "tamanho": len(store.fila_solicitacoes_ausencia),
        "complexidade": "O(1) enfileirar/desenfileirar com ponteiros inicio/fim",
        "cabeca": solicitacoes_dados[0] if solicitacoes_dados else None,
        "elementos": solicitacoes_dados,
    }

    pilha_ids = store.historico_realocacoes.para_lista()
    realocacoes_dados: list[dict] = []
    for rid in pilha_ids:
        r = store.buscar_realocacao(rid)
        if r is None:
            continue
        cond = store.buscar_condominio(r.condominio_id)
        f_origem_nome = r.fiscal_origem_id
        f_destino_nome = r.fiscal_destino_id
        try:
            f_origem_nome = store.buscar_fiscal(r.fiscal_origem_id).nome
        except Exception:
            pass
        try:
            f_destino_nome = store.buscar_fiscal(r.fiscal_destino_id).nome
        except Exception:
            pass
        realocacoes_dados.append({
            "id": r.id,
            "condominio_id": r.condominio_id,
            "condominio_nome": cond.nome if cond else r.condominio_id,
            "de": f_origem_nome,
            "para": f_destino_nome,
            "ativa": r.ativa,
        })
    pilha_info = {
        "classe": "Pilha",
        "disciplina": "LIFO (Last In, First Out)",
        "tamanho": len(store.historico_realocacoes),
        "complexidade": "O(1) empilhar/desempilhar com ponteiro topo",
        "topo": realocacoes_dados[0] if realocacoes_dados else None,
        "elementos": realocacoes_dados,
    }

    return jsonify({
        "vetor": vetor_info,
        "lista_encadeada": lista_info,
        "fila": fila_info,
        "pilha": pilha_info,
    })


@app.post("/api/reset")
def resetar():
    autorizado, erro_resp = _exigir_papeis(PAPEL_ADMIN)
    if not autorizado:
        return erro_resp

    with _lock:
        _estado.update(_inicializar_estado())
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host=config.host, port=config.porta, debug=config.debug)
