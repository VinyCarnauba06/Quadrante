import os
import pytest

from backend.domain.fiscal import PAPEL_ADMIN, PAPEL_OPERADOR, PAPEL_FISCAL_CAMPO
from backend.repository.store import Store
from backend.seed.loader import carregar
from backend.service.auth_service import (
    AuthService,
    CredenciaisInvalidasError,
    UsuarioInativoError,
    gerar_hash_senha,
    verificar_senha,
)

BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO_SEED: str = os.path.join(BASE_DIR, "backend", "seed", "dados.json")


def test_hashing_e_verificacao_de_senha():
    hash_hex, salt_hex = gerar_hash_senha("senha123")
    assert len(hash_hex) == 64
    assert len(salt_hex) == 32
    assert verificar_senha("senha123", salt_hex, hash_hex) is True
    assert verificar_senha("senha_errada", salt_hex, hash_hex) is False
    assert verificar_senha("", salt_hex, hash_hex) is False
    assert verificar_senha("senha123", "", hash_hex) is False


def test_autenticacao_com_credenciais_corretas():
    store = Store()
    carregar(CAMINHO_SEED, store)
    auth = AuthService(store)

    admin = auth.autenticar("admin@quadrante.com", "admin123")
    assert admin.nome == "Administrador"
    assert admin.papel == PAPEL_ADMIN
    assert admin.is_admin() is True

    operador = auth.autenticar("operador@quadrante.com", "operador123")
    assert operador.nome == "Operador de Despacho"
    assert operador.papel == PAPEL_OPERADOR
    assert operador.is_operador() is True

    fiscal = auth.autenticar("marcos@exemplo.com", "fiscal123")
    assert fiscal.nome == "MARCOS"
    assert fiscal.papel == PAPEL_FISCAL_CAMPO
    assert fiscal.is_fiscal_campo() is True


def test_autenticacao_falha_com_senha_errada():
    store = Store()
    carregar(CAMINHO_SEED, store)
    auth = AuthService(store)

    with pytest.raises(CredenciaisInvalidasError):
        auth.autenticar("admin@quadrante.com", "senha_incorreta")


def test_autenticacao_falha_com_usuario_inexistente():
    store = Store()
    carregar(CAMINHO_SEED, store)
    auth = AuthService(store)

    with pytest.raises(CredenciaisInvalidasError):
        auth.autenticar("inexistente@quadrante.com", "qualquer123")


def test_autenticacao_falha_com_usuario_inativo():
    store = Store()
    carregar(CAMINHO_SEED, store)
    fiscal = store.buscar_por_email("marcos@exemplo.com")
    assert fiscal is not None
    fiscal.ativo = False

    auth = AuthService(store)
    with pytest.raises(UsuarioInativoError):
        auth.autenticar("marcos@exemplo.com", "fiscal123")


def test_endpoints_auth_e_rbac_por_perfil():
    from app import app
    client = app.test_client()

    resp_me_unauth = client.get("/api/auth/me")
    assert resp_me_unauth.status_code == 200
    assert resp_me_unauth.json["autenticado"] is False

    resp_contas = client.get("/api/auth/contas-demo")
    assert resp_contas.status_code == 200
    papeis_demo = {c["papel"] for c in resp_contas.json}
    assert PAPEL_ADMIN in papeis_demo
    assert PAPEL_OPERADOR in papeis_demo
    assert PAPEL_FISCAL_CAMPO in papeis_demo

    resp_login_errado = client.post("/api/auth/login", json={"email": "admin@quadrante.com", "senha": "errada"})
    assert resp_login_errado.status_code == 401

    resp_login_fiscal = client.post("/api/auth/login", json={"email": "marcos@exemplo.com", "senha": "fiscal123"})
    assert resp_login_fiscal.status_code == 200
    fiscal_id = resp_login_fiscal.json["usuario"]["id"]

    resp_me_fiscal = client.get("/api/auth/me")
    assert resp_me_fiscal.status_code == 200
    assert resp_me_fiscal.json["autenticado"] is True
    assert resp_me_fiscal.json["usuario"]["papel"] == PAPEL_FISCAL_CAMPO

    resp_rota_propria = client.get(f"/api/fiscais/{fiscal_id}/rota")
    assert resp_rota_propria.status_code == 200

    resp_rota_alheia = client.get("/api/fiscais/fisc-023/rota")
    assert resp_rota_alheia.status_code == 403

    resp_cluster_fiscal = client.post("/api/clustering/aplicar", json={"atribuicoes": []})
    assert resp_cluster_fiscal.status_code == 403

    resp_cond_fiscal = client.post("/api/condominios", json={"nome": "X"})
    assert resp_cond_fiscal.status_code == 403

    client.post("/api/auth/logout")

    resp_login_op = client.post("/api/auth/login", json={"email": "operador@quadrante.com", "senha": "operador123"})
    assert resp_login_op.status_code == 200
    assert resp_login_op.json["usuario"]["papel"] == PAPEL_OPERADOR

    resp_cluster_op = client.post("/api/clustering/aplicar", json={"atribuicoes": []})
    assert resp_cluster_op.status_code == 403

    resp_rota_op = client.get("/api/fiscais/fisc-023/rota")
    assert resp_rota_op.status_code == 200

    client.post("/api/auth/logout")

    resp_login_admin = client.post("/api/auth/login", json={"email": "admin@quadrante.com", "senha": "admin123"})
    assert resp_login_admin.status_code == 200
    assert resp_login_admin.json["usuario"]["papel"] == PAPEL_ADMIN

    resp_cluster_admin = client.post("/api/clustering/aplicar", json={"atribuicoes": []})
    assert resp_cluster_admin.status_code == 200

