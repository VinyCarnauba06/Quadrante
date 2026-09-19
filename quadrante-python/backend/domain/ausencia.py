from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

MOTIVO_FERIAS = "ferias"
MOTIVO_FALTA = "falta"
MOTIVO_LICENCA = "licenca"
MOTIVO_OUTRO = "outro"


@dataclass
class Ausencia:
    id: str
    fiscal_id: str
    data_inicio: datetime
    data_fim: datetime
    motivo: str = MOTIVO_OUTRO
    observacao: str = ""
    criado_em: datetime = field(default_factory=datetime.utcnow)

    def cobre(self, data: datetime) -> bool:
        d = data.replace(hour=0, minute=0, second=0, microsecond=0)
        return self.data_inicio <= d <= self.data_fim


@dataclass
class Realocacao:
    id: str
    ausencia_id: str
    condominio_id: str
    fiscal_origem_id: str
    fiscal_destino_id: str
    distancia_metros: float
    ativa: bool = True
    criado_em: datetime = field(default_factory=datetime.utcnow)
    revertida_em: Optional[datetime] = None
