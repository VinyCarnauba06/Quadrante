from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

GEOCODE_PENDENTE = "pendente"
GEOCODE_OK = "ok"
GEOCODE_PRECISA_REVISAO = "precisa_revisao"


@dataclass
class Condominio:
    id: str
    nome: str
    fiscal_titular_id: str
    endereco_formatado: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geocode_status: str = GEOCODE_OK
    criado_em: datetime = field(default_factory=datetime.utcnow)

    def tem_localizacao(self) -> bool:
        """(0,0) é o valor gravado quando a geocodificação falhou e nunca é
        uma localização real — tratamos como "sem localização" mesmo que os
        campos não sejam None."""
        if self.latitude is None or self.longitude is None:
            return False
        return self.latitude != 0 or self.longitude != 0
