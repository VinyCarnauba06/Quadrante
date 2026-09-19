import hashlib
import hmac
import secrets
from typing import Optional

from backend.domain.fiscal import Fiscal

ITERACOES_PBKDF2: int = 100_000
ALGORITMO_HASH: str = "sha256"


def gerar_hash_senha(senha: str, salt_hex: Optional[str] = None) -> tuple[str, str]:
    salt: bytes = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    chave_derivada: bytes = hashlib.pbkdf2_hmac(
        ALGORITMO_HASH,
        senha.encode("utf-8"),
        salt,
        ITERACOES_PBKDF2,
    )
    return chave_derivada.hex(), salt.hex()


def verificar_senha(senha: str, salt_hex: str, hash_hex: str) -> bool:
    if not salt_hex or not hash_hex or not senha:
        return False
    try:
        salt: bytes = bytes.fromhex(salt_hex)
        hash_esperado: bytes = bytes.fromhex(hash_hex)
    except ValueError:
        return False

    chave_calculada: bytes = hashlib.pbkdf2_hmac(
        ALGORITMO_HASH,
        senha.encode("utf-8"),
        salt,
        ITERACOES_PBKDF2,
    )
    return hmac.compare_digest(chave_calculada, hash_esperado)


class CredenciaisInvalidasError(Exception):
    pass


class UsuarioInativoError(Exception):
    pass


class AuthService:
    def __init__(self, store) -> None:
        self._store = store

    def autenticar(self, email: str, senha: str) -> Fiscal:
        email_limpo: str = email.strip().lower()
        fiscal: Optional[Fiscal] = self._store.buscar_por_email(email_limpo)
        if fiscal is None:
            verificar_senha("dummy", "00" * 16, "00" * 32)
            raise CredenciaisInvalidasError("E-mail ou senha incorretos.")

        if not fiscal.ativo:
            raise UsuarioInativoError("Usuário inativo no sistema.")

        if not verificar_senha(senha, fiscal.salt, fiscal.senha_hash):
            raise CredenciaisInvalidasError("E-mail ou senha incorretos.")

        return fiscal

    def definir_senha(self, fiscal_id: str, nova_senha: str) -> None:
        hash_hex, salt_hex = gerar_hash_senha(nova_senha)
        self._store.atualizar_credenciais(fiscal_id, hash_hex, salt_hex)
