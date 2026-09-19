import os
from dataclasses import dataclass
from typing import MutableMapping, Optional

HOSTS_LOCAIS = {"127.0.0.1", "localhost", "::1"}
VALORES_VERDADEIROS = {"1", "true", "yes", "sim", "on"}


class ConfiguracaoInvalida(ValueError):
    pass


@dataclass(frozen=True)
class Configuracao:
    host: str
    porta: int
    debug: bool
    geoapify_chave: Optional[str]


def carregar_env(caminhos: list[str], ambiente: MutableMapping[str, str]) -> None:
    for caminho in caminhos:
        if not os.path.isfile(caminho):
            continue
        with open(caminho, encoding="utf-8-sig") as arquivo:
            for linha in arquivo:
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                nome, valor = linha.split("=", 1)
                valor = valor.strip()
                if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
                    valor = valor[1:-1]
                ambiente.setdefault(nome.strip(), valor)


def carregar_configuracao(base_dir: str, ambiente: Optional[MutableMapping[str, str]] = None) -> Configuracao:
    if ambiente is None:
        ambiente = os.environ
    carregar_env(
        [os.path.join(base_dir, ".env"), os.path.join(os.path.dirname(base_dir), ".env")],
        ambiente,
    )

    host = ambiente.get("QUADRANTE_HOST", "127.0.0.1").strip() or "127.0.0.1"
    texto_porta = ambiente.get("QUADRANTE_PORT", "5000").strip() or "5000"
    try:
        porta = int(texto_porta)
    except ValueError:
        raise ConfiguracaoInvalida(f"QUADRANTE_PORT inválida: {texto_porta!r}") from None
    if not 1 <= porta <= 65535:
        raise ConfiguracaoInvalida(f"QUADRANTE_PORT fora do intervalo 1-65535: {porta}")

    debug = ambiente.get("QUADRANTE_DEBUG", "0").strip().lower() in VALORES_VERDADEIROS
    if debug and host not in HOSTS_LOCAIS:
        raise ConfiguracaoInvalida("QUADRANTE_DEBUG=1 só é permitido com QUADRANTE_HOST=127.0.0.1")

    chave = ambiente.get("GEOAPIFY_API_KEY", "").strip() or None
    return Configuracao(host=host, porta=porta, debug=debug, geoapify_chave=chave)
