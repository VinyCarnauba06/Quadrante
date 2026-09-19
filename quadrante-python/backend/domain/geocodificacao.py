from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ResultadoGeocodificacao:
    endereco: str
    latitude: float
    longitude: float
    bairro: str = ""
    confianca: Optional[float] = None
