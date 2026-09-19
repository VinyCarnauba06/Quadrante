from dataclasses import dataclass, field


@dataclass
class AtribuicaoSugerida:
    condominio_id: str
    condominio_nome: str
    fiscal_atual_id: str
    fiscal_atual_nome: str
    fiscal_sugerido_id: str
    fiscal_sugerido_nome: str
    mudou: bool
    distancia_ate_centroide_metros: float = 0.0


@dataclass
class SugestaoClustering:
    total_condominios: int = 0
    total_mudancas: int = 0
    atribuicoes: list = field(default_factory=list)
