import io
import json
import urllib.error

import pytest

import app as aplicacao
from backend.domain.geocodificacao import ResultadoGeocodificacao
from backend.infra.geoapify import GeoapifyGeocodificador
from backend.service.cadastro_service import CadastroService, DadosInvalidosError
from backend.service.geocoding_service import (
    GeocodificacaoFalhouError,
    GeocodificacaoIndisponivelError,
    GeocodificadorAusente,
)
from tests.test_services import _store_pequeno

PERTO_DE_ANA = ResultadoGeocodificacao(endereco="Rua A, 10, Farol, Maceió - AL", latitude=-9.601, longitude=-35.701, bairro="Farol", confianca=0.9)
PERTO_DE_CARLA = ResultadoGeocodificacao(endereco="Rua C, 20, Jaraguá, Maceió - AL", latitude=-9.899, longitude=-35.899, bairro="Jaraguá", confianca=0.8)


class GeocodificadorFalso:
    def __init__(self, resultados):
        self._resultados = resultados
        self.chamadas = []

    def buscar(self, texto, limite=5):
        self.chamadas.append((texto, limite))
        return self._resultados


class RespostaFalsa(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _abrir_com(corpo):
    def abrir(url, timeout):
        abrir.url = url
        return RespostaFalsa(json.dumps(corpo).encode("utf-8"))

    return abrir


def _abrir_com_erro(erro):
    def abrir(url, timeout):
        raise erro

    return abrir


def test_localizar_sugere_o_fiscal_de_campo_mais_proximo():
    store, a, b, c, coord = _store_pequeno()
    servico = CadastroService(store, GeocodificadorFalso([PERTO_DE_ANA, PERTO_DE_CARLA]))

    candidatos = servico.localizar("rua")

    assert [x.destino.fiscal.id for x in candidatos] == [a, c]
    assert all(x.destino.distancia_metros >= 0 for x in candidatos)


def test_localizar_ignora_coordenador_mesmo_sendo_o_mais_proximo():
    store, a, b, c, coord = _store_pequeno()
    perto_do_coordenador = ResultadoGeocodificacao(endereco="x", latitude=-9.50, longitude=-35.50)
    servico = CadastroService(store, GeocodificadorFalso([perto_do_coordenador]))

    candidato = servico.localizar("rua")[0]

    assert candidato.destino.fiscal.id != coord


def test_localizar_rejeita_busca_curta_sem_chamar_api():
    store, *_ = _store_pequeno()
    geocodificador = GeocodificadorFalso([])
    servico = CadastroService(store, geocodificador)

    with pytest.raises(DadosInvalidosError):
        servico.localizar("ab")

    assert geocodificador.chamadas == []


def test_cadastrar_entra_na_carteira_do_fiscal_mais_proximo():
    store, a, b, c, coord = _store_pequeno()
    servico = CadastroService(store, GeocodificadorFalso([]))
    antes = len(store.listar_por_fiscal(a))

    condominio, destino = servico.cadastrar("  Residencial Novo  ", PERTO_DE_ANA.endereco, PERTO_DE_ANA.latitude, PERTO_DE_ANA.longitude)

    assert destino.fiscal.id == a
    assert condominio.nome == "Residencial Novo"
    assert condominio.fiscal_titular_id == a
    assert len(store.listar_por_fiscal(a)) == antes + 1
    assert store.buscar_condominio(condominio.id) is condominio
    assert condominio.tem_localizacao()


@pytest.mark.parametrize(
    "nome,latitude,longitude",
    [
        ("", -9.6, -35.7),
        ("x" * 121, -9.6, -35.7),
        ("Ok", 0, 0),
        ("Ok", 95, -35.7),
        ("Ok", "abc", -35.7),
        ("Ok", True, -35.7),
        ("Ok", None, None),
        ("Ok", -23.55, -46.63),
    ],
)
def test_cadastrar_rejeita_dados_invalidos(nome, latitude, longitude):
    store, *_ = _store_pequeno()
    servico = CadastroService(store, GeocodificadorFalso([]))
    total = len(store.listar_todos_geocodificados())

    with pytest.raises(DadosInvalidosError):
        servico.cadastrar(nome, "endereco", latitude, longitude)

    assert len(store.listar_todos_geocodificados()) == total


def test_geocodificador_ausente_explica_como_configurar():
    with pytest.raises(GeocodificacaoIndisponivelError, match="GEOAPIFY_API_KEY"):
        GeocodificadorAusente().buscar("rua")


def test_geoapify_converte_resposta_e_envia_parametros():
    abrir = _abrir_com(
        {
            "results": [
                {"lat": -9.66, "lon": -35.71, "formatted": "Rua X, Ponta Verde, Maceió", "suburb": "Ponta Verde", "rank": {"confidence": 0.95}},
                {"lat": -9.67, "lon": -35.72, "formatted": "Rua Y", "district": "Farol"},
                {"formatted": "sem coordenada"},
            ]
        }
    )
    geocodificador = GeoapifyGeocodificador("segredo", abrir=abrir)

    resultados = geocodificador.buscar("Rua X, 10", limite=3)

    assert [r.bairro for r in resultados] == ["Ponta Verde", "Farol"]
    assert resultados[0].confianca == 0.95
    assert resultados[1].confianca is None
    assert "text=Rua+X%2C+10" in abrir.url
    assert "limit=3" in abrir.url
    assert "apiKey=segredo" in abrir.url
    assert "circle%3A-35.7089%2C-9.6498%2C30000" in abrir.url


@pytest.mark.parametrize("codigo,excecao", [(401, GeocodificacaoIndisponivelError), (403, GeocodificacaoIndisponivelError), (429, GeocodificacaoFalhouError), (500, GeocodificacaoFalhouError)])
def test_geoapify_traduz_erros_http_sem_vazar_a_chave(codigo, excecao):
    erro = urllib.error.HTTPError("https://api.geoapify.com/x?apiKey=segredo", codigo, "erro", {}, None)
    geocodificador = GeoapifyGeocodificador("segredo", abrir=_abrir_com_erro(erro))

    with pytest.raises(excecao) as capturado:
        geocodificador.buscar("rua x")

    assert "segredo" not in str(capturado.value)


@pytest.mark.parametrize("erro", [urllib.error.URLError("sem rede"), TimeoutError("lento"), ValueError("json ruim")])
def test_geoapify_traduz_falhas_de_rede(erro):
    geocodificador = GeoapifyGeocodificador("segredo", abrir=_abrir_com_erro(erro))

    with pytest.raises(GeocodificacaoFalhouError):
        geocodificador.buscar("rua x")


@pytest.fixture
def cliente(monkeypatch):
    store, a, b, c, coord = _store_pequeno()
    servico = CadastroService(store, GeocodificadorFalso([PERTO_DE_ANA]))
    monkeypatch.setitem(aplicacao._estado, "cadastro", servico)
    return aplicacao.app.test_client(), store, a


def test_endpoint_geocodificar_devolve_candidatos_com_fiscal_sugerido(cliente):
    http, store, a = cliente

    resposta = http.get("/api/geocodificar?q=rua a")

    assert resposta.status_code == 200
    candidato = resposta.get_json()["candidatos"][0]
    assert candidato["fiscal_sugerido_id"] == a
    assert candidato["bairro"] == "Farol"
    assert candidato["latitude"] == -9.601


def test_endpoint_geocodificar_busca_curta_retorna_400(cliente):
    http, *_ = cliente
    assert http.get("/api/geocodificar?q=a").status_code == 400


def test_endpoint_geocodificar_sem_chave_retorna_503(monkeypatch):
    store, *_ = _store_pequeno()
    monkeypatch.setitem(aplicacao._estado, "cadastro", CadastroService(store, GeocodificadorAusente()))

    resposta = aplicacao.app.test_client().get("/api/geocodificar?q=rua a")

    assert resposta.status_code == 503
    assert "GEOAPIFY_API_KEY" in resposta.get_json()["erro"]


def test_endpoint_cadastrar_cria_condominio_na_carteira(cliente):
    http, store, a = cliente
    antes = len(store.listar_por_fiscal(a))

    resposta = http.post("/api/condominios", json={"nome": "Novo", "endereco": "Rua A", "latitude": -9.601, "longitude": -35.701})

    assert resposta.status_code == 201
    corpo = resposta.get_json()
    assert corpo["fiscal_id"] == a
    assert len(store.listar_por_fiscal(a)) == antes + 1


def test_endpoint_cadastrar_rejeita_payload_invalido(cliente):
    http, *_ = cliente
    assert http.post("/api/condominios", json={"nome": "", "latitude": -9.6, "longitude": -35.7}).status_code == 400
    assert http.post("/api/condominios", data="nao-json", content_type="text/plain").status_code == 400
