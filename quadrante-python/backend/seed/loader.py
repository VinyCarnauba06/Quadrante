"""Carrega seed/dados.json (dados sintéticos: nomes fictícios, coordenadas
reais de Maceió-AL) para dentro de um repository.store.Store — mesmo arquivo
usado pelo núcleo em Go, sem duplicar massa de teste."""

import json
from dataclasses import dataclass

from backend.domain.condominio import GEOCODE_OK
from backend.domain.fiscal import PAPEL_ADMIN, PAPEL_OPERADOR, PAPEL_FISCAL_CAMPO, PAPEL_COORDENADOR
from backend.repository.store import Store
from backend.service.auth_service import gerar_hash_senha


@dataclass
class Resultado:
    fiscais: int = 0
    condominios: int = 0


def carregar(caminho: str, store: Store) -> Resultado:
    with open(caminho, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    resultado = Resultado()

    hash_admin, salt_admin = gerar_hash_senha("admin123")
    store.seed_fiscal("Administrador", "admin@quadrante.com", PAPEL_ADMIN, hash_admin, salt_admin)
    resultado.fiscais += 1

    hash_op, salt_op = gerar_hash_senha("operador123")
    store.seed_fiscal("Operador de Despacho", "operador@quadrante.com", PAPEL_OPERADOR, hash_op, salt_op)
    resultado.fiscais += 1

    for fiscal in dados["fiscais"]:
        papel = fiscal.get("papel") or PAPEL_FISCAL_CAMPO
        senha_padrao = "admin123" if papel == PAPEL_COORDENADOR else "fiscal123"
        hash_senha, salt = gerar_hash_senha(fiscal.get("senha") or senha_padrao)
        fiscal_id = store.seed_fiscal(fiscal["nome"], fiscal.get("email", ""), papel, hash_senha, salt)
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
