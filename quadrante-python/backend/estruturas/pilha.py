from typing import Optional, TypeVar

T = TypeVar("T")


class _No:
    __slots__ = ("valor", "proximo")

    def __init__(self, valor):
        self.valor = valor
        self.proximo: Optional["_No"] = None


class PilhaVaziaError(Exception):
    pass


class Pilha:
    """Pilha LIFO sobre lista encadeada própria, com topo O(1).

    Mapeada ao histórico de realocações: desfazer sempre reverte a
    movimentação mais recente primeiro — é literalmente uma semântica de
    pilha, não uma escolha arbitrária de estrutura.
    """

    def __init__(self):
        self._topo: Optional[_No] = None
        self._tamanho = 0

    def __len__(self) -> int:
        return self._tamanho

    def esta_vazia(self) -> bool:
        return self._topo is None

    def empilhar(self, valor: T) -> None:
        no = _No(valor)
        no.proximo = self._topo
        self._topo = no
        self._tamanho += 1

    def desempilhar(self) -> T:
        if self._topo is None:
            raise PilhaVaziaError("pilha vazia")
        no = self._topo
        self._topo = no.proximo
        self._tamanho -= 1
        return no.valor

    def topo_valor(self) -> T:
        if self._topo is None:
            raise PilhaVaziaError("pilha vazia")
        return self._topo.valor

    def para_lista(self) -> list:
        """Do topo (mais recente) para a base (mais antigo)."""
        saida = []
        atual = self._topo
        while atual is not None:
            saida.append(atual.valor)
            atual = atual.proximo
        return saida

    def __repr__(self) -> str:
        return f"Pilha(topo->base={self.para_lista()!r})"
