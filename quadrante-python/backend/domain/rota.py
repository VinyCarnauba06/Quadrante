from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class GeoPonto:
    id: str
    latitude: float
    longitude: float


@dataclass
class RotaParada:
    condominio_id: str
    ordem: int
    condominio_nome: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    visitado_em: Optional[datetime] = None


@dataclass
class Rota:
    fiscal_id: str
    data_rota: datetime
    distancia_total_metros: float = 0.0
    paradas: list = field(default_factory=list)
    gerada_em: datetime = field(default_factory=datetime.utcnow)
