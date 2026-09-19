# Quadrante — versão Python (Estruturas de Dados)

Reescrita completa, em Python, do núcleo do **Quadrante**: um sistema de
**roteirização e divisão territorial por proximidade geográfica** para
equipes de fiscalização de campo. Implementa as quatro estruturas exigidas
pela disciplina **e** resolve o problema real com os mesmos três
algoritmos do núcleo original em Go — sobre os dados reais (coordenadas de
Maceió-AL, 9 fiscais, 127 condomínios).

## Rodar

```sh
pip install -r requirements.txt
python app.py            # sobe em http://localhost:5000
pytest                    # 22 testes: estruturas + serviços
```

## Estrutura de pastas — backend, frontend e testes bem separados

```
quadrante-python/
├── app.py                     # ÚNICO ponto de contato entre backend e frontend:
│                                monta as rotas Flask, aponta pros templates/static
│                                do frontend/ e chama os serviços do backend/
├── requirements.txt
├── README.md
│
├── backend/                   # TUDO que é lógica — zero HTML/CSS/JS aqui dentro
│   ├── domain/                  entidades puras: Fiscal, Condominio, Ausencia,
│   │                            Realocacao, Rota, GeoPonto, AtribuicaoSugerida
│   ├── estruturas/              Vetor, ListaEncadeada, Pilha, Fila — implementadas
│   │                            do zero (sem list.append/pop, sem collections.deque)
│   ├── repository/              Store in-memory — usa as estruturas acima como
│   │                            containers REAIS do estado do sistema
│   ├── service/                 os 3 algoritmos:
│   │   ├── routing_service.py       TSP (nearest-neighbor + 2-opt)
│   │   ├── clustering_service.py    k-means geográfico + rebalanceamento
│   │   ├── reallocation_service.py  alocação gulosa + fila/pilha de negócio
│   │   └── mapa.py                  gera o PNG do mapa (matplotlib) — única parte
│   │                                do backend que "sabe" que existe apresentação
│   └── seed/                    dados.json real (Maceió-AL) + loader
│
├── frontend/                  # TUDO que é apresentação — zero lógica de negócio aqui
│   ├── templates/index.html     página única, responsiva desktop-first
│   └── static/
│       ├── css/style.css
│       └── js/app.js             só faz fetch() na API e atualiza o DOM
│
└── tests/                     pytest — testa só o backend (frontend não tem lógica
                                própria pra testar), espelha os *_test.go originais
    ├── test_estruturas.py       as 4 estruturas isoladamente
    └── test_services.py         os 3 serviços (com seed real + cenários sintéticos)
```

**Regra de dependência (via de mão única):** `backend/` nunca importa nada
de `frontend/` nem de `app.py` — os algoritmos e as estruturas de dados não
sabem que existe uma página web por cima; poderiam virar uma CLI ou uma API
para outro cliente sem mudar uma linha. `frontend/` nunca contém lógica de
negócio — `static/js/app.js` só chama a API (`fetch`) e pinta o resultado
na tela, nenhuma conta de distância ou decisão de realocação acontece no
navegador. `app.py` é a única peça que conhece os dois lados.

## Onde está cada conceito de ED

| Estrutura | Arquivo | Implementação | Mapeamento no domínio |
|---|---|---|---|
| **Vetor** | `backend/estruturas/vetor.py` | array de capacidade fixa que dobra ao encher — sem `list.append` como caixa-preta | cadastro de fiscais (`Store.fiscais`): poucas inserções, muita leitura |
| **Lista encadeada** | `backend/estruturas/lista_encadeada.py` | nós com ponteiro `proximo`, sem `collections.deque` | carteira de condomínios de **cada** fiscal — alta rotatividade por realocação; religar dois ponteiros é O(1) contra deslocar um vetor |
| **Pilha (LIFO)** | `backend/estruturas/pilha.py` | lista encadeada própria, ponteiro de topo | histórico de realocações (`Store.historico_realocacoes`) — desfazer manual sempre reverte a mudança mais recente primeiro |
| **Fila (FIFO)** | `backend/estruturas/fila.py` | lista encadeada com ponteiros de início e fim, O(1) nas duas pontas | solicitações de ausência pendentes (`Store.fila_solicitacoes_ausencia`) — processadas na ordem cronológica de chegada |

Nenhuma das quatro é decorativa: cada uma é a estrutura que o
`backend/repository/store.py` usa de verdade para guardar o estado do
sistema — troque uma peça e o resto do código quebra, porque as operações
(`atualizar_fiscal_titular`, `desfazer_ultima_realocacao`,
`processar_proxima_solicitacao`) dependem do comportamento específico da
estrutura, não de uma lista genérica por trás.

## Os três algoritmos (a "essência" preservada do núcleo em Go)

1. **TSP heurístico** (`backend/service/routing_service.py`) — matriz de
   distância Haversine + nearest-neighbor + 2-opt, caminho aberto. Decide a
   ordem de visita de menor distância dentro da carteira de um fiscal.
2. **k-means geográfico + rebalanceamento** (`backend/service/clustering_service.py`)
   — sugere redividir toda a base entre os fiscais de campo, com centróides
   iniciais não-aleatórios (posição atual de cada um) para preservar a
   divisão vigente e só mover quem está mal alocado.
3. **Alocação gulosa com limite de carga** (`backend/service/reallocation_service.py`)
   — quando um fiscal entra em ausência, redistribui sua carteira para os
   fiscais mais próximos geograficamente, com desempate determinístico
   (distância → carga já recebida → ID) e reversão automática ao fim do
   período.

A matriz de distância e os vetores de controle internos desses algoritmos
(`visitado`, `ordem`, a matriz n×n) usam listas nativas do Python de
propósito: não são o "Vetor" do syllabus — são estado escalar de um
algoritmo numérico, exatamente como o Go usa `slice` ali. As quatro
estruturas do syllabus vivem no `Store`, onde representam coleções de
domínio, não scratch de algoritmo.

## Frontend

Página única em HTML/CSS/JS puro (sem framework, sem build step — sobe
direto do Flask). Layout em duas colunas no desktop (lista de fiscais e
ações à esquerda, mapa e clustering à direita), colapsa para uma coluna em
telas estreitas. O mapa é gerado no backend com matplotlib a partir das
coordenadas reais e servido como PNG — o frontend só exibe a imagem.

## Roteiro de apresentação (5-8 min)

1. **Contexto (1 min):** Prolar AGE fiscaliza ~130 condomínios em Maceió com
   fiscais de campo. Três problemas reais: em que ordem visitar a carteira,
   como redividir a base entre fiscais, o que fazer quando um fiscal sai de
   férias.
2. **As quatro estruturas, direto no código (2 min):** abrir
   `backend/estruturas/pilha.py` e `backend/estruturas/fila.py` — mostrar
   que são implementadas com nós e ponteiros, não `list.append`. Explicar
   por que cada uma foi escolhida para o seu papel (não é aleatório: Pilha
   porque desfazer é LIFO por natureza; Fila porque atendimento de
   solicitação é FIFO por natureza).
3. **Demo ao vivo (3-4 min):** abrir a página, mostrar o mapa geral, clicar
   num fiscal (mostra rota otimizada mudando o mapa), registrar uma
   ausência (mostrar a fila crescer), processar a fila (mostra realocação +
   histórico), desfazer (mostra a pilha reagindo), rodar o k-means e
   mostrar a sugestão de redistribuição.
4. **Fechamento (30s):** essa é uma versão real de produção da empresa do
   apresentador — os dados geográficos são reais, os algoritmos são os
   mesmos que já rodam em produção; o que mudou pra caber na disciplina foi
   a persistência (agora em memória, sobre as quatro estruturas) e a
   ausência de HTTP/auth de produção.

## Dados

`backend/seed/dados.json`: nomes de fiscais e condomínios são fictícios; as
coordenadas correspondem a pontos reais de Maceió-AL, usadas como massa de
teste geográfica (geocodificação falsa não plota certo no mapa).
