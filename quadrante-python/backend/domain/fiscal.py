from dataclasses import dataclass, field
from datetime import datetime

PAPEL_ADMIN = "admin"
PAPEL_OPERADOR = "operador"
PAPEL_FISCAL_CAMPO = "fiscal_campo"
PAPEL_COORDENADOR = "coordenador"


@dataclass
class Fiscal:
    id: str
    nome: str
    papel: str
    email: str = ""
    ativo: bool = True
    senha_hash: str = ""
    salt: str = ""
    criado_em: datetime = field(default_factory=datetime.utcnow)

    def is_admin(self) -> bool:
        return self.papel in (PAPEL_ADMIN, PAPEL_COORDENADOR)

    def is_operador(self) -> bool:
        return self.papel == PAPEL_OPERADOR

    def is_fiscal_campo(self) -> bool:
        return self.papel == PAPEL_FISCAL_CAMPO

    def is_coordenador(self) -> bool:
        return self.papel == PAPEL_COORDENADOR

