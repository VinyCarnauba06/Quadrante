import pytest

from backend.estruturas import Vetor, ListaEncadeada, Pilha, PilhaVaziaError, Fila, FilaVaziaError


def test_vetor_adiciona_e_cresce_alem_da_capacidade_inicial():
    v = Vetor(capacidade_inicial=2)
    for i in range(10):
        v.adicionar(i)
    assert len(v) == 10
    assert v.para_lista() == list(range(10))


def test_vetor_remover_em_desloca_elementos():
    v = Vetor()
    for i in range(5):
        v.adicionar(i)
    removido = v.remover_em(2)
    assert removido == 2
    assert v.para_lista() == [0, 1, 3, 4]


def test_vetor_encontrar_e_filtrar():
    v = Vetor()
    for i in range(5):
        v.adicionar(i)
    assert v.encontrar(lambda x: x == 3) == 3
    assert v.encontrar(lambda x: x == 99) is None
    assert v.filtrar(lambda x: x % 2 == 0).para_lista() == [0, 2, 4]


def test_vetor_indice_invalido_estoura():
    v = Vetor()
    v.adicionar(1)
    with pytest.raises(IndexError):
        v.obter(5)


def test_lista_encadeada_insercao_e_remocao():
    lst = ListaEncadeada()
    lst.inserir_no_fim("a")
    lst.inserir_no_fim("b")
    lst.inserir_no_inicio("z")
    assert lst.para_lista() == ["z", "a", "b"]

    removido = lst.remover_onde(lambda x: x == "a")
    assert removido == "a"
    assert lst.para_lista() == ["z", "b"]
    assert len(lst) == 2


def test_lista_encadeada_remover_inexistente_retorna_none():
    lst = ListaEncadeada()
    lst.inserir_no_fim(1)
    assert lst.remover_onde(lambda x: x == 99) is None
    assert len(lst) == 1


def test_pilha_lifo():
    p = Pilha()
    p.empilhar(1)
    p.empilhar(2)
    p.empilhar(3)
    assert p.topo_valor() == 3
    assert p.desempilhar() == 3
    assert p.desempilhar() == 2
    assert len(p) == 1


def test_pilha_vazia_estoura():
    p = Pilha()
    with pytest.raises(PilhaVaziaError):
        p.desempilhar()


def test_fila_fifo():
    f = Fila()
    f.enfileirar("primeiro")
    f.enfileirar("segundo")
    f.enfileirar("terceiro")
    assert f.frente_valor() == "primeiro"
    assert f.desenfileirar() == "primeiro"
    assert f.desenfileirar() == "segundo"
    assert len(f) == 1


def test_fila_vazia_estoura():
    f = Fila()
    with pytest.raises(FilaVaziaError):
        f.desenfileirar()


def test_fila_reaproveita_ponteiro_fim_apos_esvaziar():
    f = Fila()
    f.enfileirar(1)
    f.desenfileirar()
    f.enfileirar(2)
    f.enfileirar(3)
    assert f.para_lista() == [2, 3]
