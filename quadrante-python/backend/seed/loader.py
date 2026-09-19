"""Carrega seed/dados.json (dados sintéticos: nomes fictícios, coordenadas
reais de Maceió-AL) para dentro de um repository.store.Store — mesmo arquivo
usado pelo núcleo em Go, sem duplicar massa de teste."""

import json
from dataclasses import dataclass

from backend.domain.condominio import GEOCODE_OK
from backend.domain.fiscal import PAPEL_FISCAL_CAMPO
from backend.repository.store import Store


@dataclass
class Resultado:
    fiscais: int = 0
    condominios: int = 0


def carregar(caminho: str, store: Store) -> Resultado:
    with open(caminho, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    resultado = Resultado()
    for fiscal in dados["fiscais"]:
        papel = fiscal.get("papel") or PAPEL_FISCAL_CAMPO
        fiscal_id = store.seed_fiscal(fiscal["nome"], fiscal.get("email", ""), papel)
        resultado.fiscais += 1

        for condominio in fiscal.get("condominios", []):
            status = condominio.get("geocode_status") or GEOCODE_OK
            store.seed_condominio(
                condominio["nome"],
                condominio.get("endereco_formatado", ""),
                condominio["latitude"],
                condominio["longitude"],
                status,
                fiscal_id,
            )
            resultado.condominios += 1

    return resultado
