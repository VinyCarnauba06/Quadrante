from typing import Optional, TypeVar

T = TypeVar("T")


class _No:
    __slots__ = ("valor", "proximo")

    def __init__(self, valor):
        self.valor = valor
        self.proximo: Optional["_No"] = None


class FilaVaziaError(Exception):
    pass


class Fila:
    """Fila FIFO sobre lista encadeada própria, com ponteiros de início e
    fim — enfileirar e desenfileirar são O(1).

    Mapeada às solicitações de ausência: processadas na ordem cronológica
    de chegada, nunca a mais recente primeiro.
    """

    def __init__(self):
        self._inicio: Optional[_No] = None
        self._fim: Optional[_No] = None
        self._tamanho = 0

    def __len__(self) -> int:
        return self._tamanho

    def esta_vazia(self) -> bool:
        return self._inicio is None

    def enfileirar(self, valor: T) -> None:
        no = _No(valor)
        if self._fim is None:
            self._inicio = no
            self._fim = no
        else:
            self._fim.proximo = no
            self._fim = no
        self._tamanho += 1

    def desenfileirar(self) -> T:
        if self._inicio is None:
            raise FilaVaziaError("fila vazia")
        no = self._inicio
        self._inicio = no.proximo
        if self._inicio is None:
            self._fim = None
        self._tamanho -= 1
        return no.valor

    def frente_valor(self) -> T:
        if self._inicio is None:
            raise FilaVaziaError("fila vazia")
        return self._inicio.valor

    def para_lista(self) -> list:
        """Da frente (próximo a saír) para o fim (chegou por último)."""
        saida = []
        atual = self._inicio
        while atual is not None:
            saida.append(atual.valor)
            atual = atual.proximo
        return saida

    def __repr__(self) -> str:
        return f"Fila(frente->fim={self.para_lista()!r})"
