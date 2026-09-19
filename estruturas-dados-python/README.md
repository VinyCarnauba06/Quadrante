# Estruturas de Dados — camada Python

`quadrante_estruturas_dados.ipynb` é o projeto da disciplina de **Estruturas de Dados**.
É uma camada didática separada do núcleo em Go: reescreve a lógica sobre uma versão
simplificada do domínio do Quadrante (fiscais, condomínios, realocação por ausência)
usando **apenas** as estruturas clássicas vistas em aula.

## O que o notebook faz

Reimplementa **do zero**, em Python puro, as quatro estruturas — sem usar
`list.append` / `list.pop` como caixa-preta e sem `collections.deque`:

| Estrutura | Implementação | Mapeamento no domínio |
|---|---|---|
| **Vetor** | array de capacidade fixa, cresce por realocação (dobra) | cadastro de fiscais — poucas inserções, muita leitura/percorrimento |
| **Lista encadeada** | nós com ponteiro `proximo`, lista simples | carteira de condomínios de cada fiscal — alta rotatividade, religa ponteiros em vez de deslocar |
| **Pilha (LIFO)** | lista encadeada própria, ponteiro de topo | histórico de realocações / desfazer manual — reverte a movimentação mais recente primeiro |
| **Fila (FIFO)** | lista encadeada com ponteiros de início e fim, O(1) | solicitações de ausência pendentes — processadas na ordem cronológica de chegada |

`SistemaQuadrante` é o orquestrador que junta as quatro: fiscais em um `Vetor`, a
carteira de cada fiscal em uma `CarteiraEncadeada`, as ausências em uma `Fila` e o
histórico em uma `Pilha`. A regra de negócio é uma alocação gulosa simplificada
(condomínio do ausente vai para quem tem menos carga; desempate por menor ID), sem o
critério geográfico da versão Go.

O notebook fecha com uma demonstração ponta a ponta e uma lista de exercícios.

## Dados

Todos os dados do notebook são **sintéticos e gerados no próprio notebook**. Não têm
relação com `seed/dados.json` do núcleo em Go.

## Rodar

Requer apenas Python 3 e Jupyter. Nenhuma dependência externa.

```sh
jupyter notebook quadrante_estruturas_dados.ipynb
```
