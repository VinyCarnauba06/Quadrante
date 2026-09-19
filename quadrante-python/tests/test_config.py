import pytest

from backend.config import ConfiguracaoInvalida, carregar_configuracao, carregar_env


def test_padroes_seguros(tmp_path):
    projeto = tmp_path / "projeto"
    projeto.mkdir()
    config = carregar_configuracao(str(projeto), {})
    assert config.host == "127.0.0.1"
    assert config.porta == 5000
    assert config.debug is False
    assert config.geoapify_chave is None


def test_le_env_do_projeto_e_nao_sobrescreve_ambiente(tmp_path):
    projeto = tmp_path / "projeto"
    projeto.mkdir()
    (projeto / ".env").write_text(
        "# comentario\nQUADRANTE_PORT=8080\nGEOAPIFY_API_KEY=\"abc123\"\nQUADRANTE_HOST=0.0.0.0\n",
        encoding="utf-8",
    )
    ambiente = {"QUADRANTE_PORT": "9000"}
    config = carregar_configuracao(str(projeto), ambiente)
    assert config.porta == 9000
    assert config.host == "0.0.0.0"
    assert config.geoapify_chave == "abc123"


def test_env_na_pasta_pai_tambem_e_lido(tmp_path):
    projeto = tmp_path / "projeto"
    projeto.mkdir()
    (tmp_path / ".env").write_text("GEOAPIFY_API_KEY=pai\n", encoding="utf-8")
    assert carregar_configuracao(str(projeto), {}).geoapify_chave == "pai"


def test_chave_vazia_vira_none(tmp_path):
    assert carregar_configuracao(str(tmp_path), {"GEOAPIFY_API_KEY": "   "}).geoapify_chave is None


def test_debug_exige_host_local(tmp_path):
    with pytest.raises(ConfiguracaoInvalida):
        carregar_configuracao(str(tmp_path), {"QUADRANTE_DEBUG": "1", "QUADRANTE_HOST": "0.0.0.0"})
    assert carregar_configuracao(str(tmp_path), {"QUADRANTE_DEBUG": "1"}).debug is True


@pytest.mark.parametrize("porta", ["abc", "0", "70000"])
def test_porta_invalida(tmp_path, porta):
    with pytest.raises(ConfiguracaoInvalida):
        carregar_configuracao(str(tmp_path), {"QUADRANTE_PORT": porta})


def test_carregar_env_ignora_arquivo_inexistente():
    ambiente = {}
    carregar_env(["/nao/existe/.env"], ambiente)
    assert ambiente == {}
