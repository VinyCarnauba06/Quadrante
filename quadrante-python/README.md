# Quadrante — versão Python (Estruturas de Dados)

Reescrita completa, em Python, do núcleo do **Quadrante**: um sistema de
**roteirização e divisão territorial por proximidade geográfica** para
equipes de fiscalização de campo. Implementa as quatro estruturas exigidas
pela disciplina **e** resolve o problema real com os mesmos três
algoritmos do núcleo original em Go — sobre os dados reais (coordenadas de
Maceió-AL, 9 fiscais, 127 condomínios).

## Rodar

```sh
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py            # sobe em http://127.0.0.1:5000
pytest                    # 57 testes: estruturas, serviços, configuração e geocodificação
```

### Configuração (`.env`)

O `.env` é lido de `quadrante-python/` (ou da pasta acima) na largada; variáveis
já definidas no terminal têm prioridade. Ele nunca é versionado — só o
`.env.example`.

| Variável | Padrão | Uso |
|---|---|---|
| `QUADRANTE_HOST` | `127.0.0.1` | Interface de rede. Use `0.0.0.0` só para abrir a demo para outra máquina. |
| `QUADRANTE_PORT` | `5000` | Porta do Flask. |
| `QUADRANTE_DEBUG` | `0` | `1` liga o recarregamento e o debugger; só é aceito com host `127.0.0.1`. |
| `GEOAPIFY_API_KEY` | vazio | Chave da Geoapify, usada em dois lugares: a **API de geocodificação** (servidor, aba "Novo") e o mapa base "Ruas e bairros (Geoapify)" (navegador). Vazia ou inválida, o mapa cai para CARTO e OpenStreetMap, e a aba "Novo" avisa que a geocodificação está desativada. |

A chave também vai para o navegador (é assim que qualquer camada de tiles
funciona). No painel da Geoapify, restrinja-a às origens `localhost` e
`127.0.0.1` em vez de deixá-la aberta.

### API de localização (Geoapify)

A aba **Novo** cadastra um condomínio a partir do endereço:

1. `GET /api/geocodificar?q=...` — o servidor chama a Geoapify Geocoding API
   (filtrada a 30 km de Maceió) e devolve até 5 candidatos com bairro,
   coordenadas, precisão e o fiscal que receberia o condomínio.
2. O candidato escolhido aparece como pin de prévia no mapa.
3. `POST /api/condominios` — valida os dados, escolhe o fiscal de campo com o
   centro de carteira mais próximo (Haversine; desempate por carga e ID;
   coordenador nunca recebe) e insere o condomínio na Lista encadeada dele.

A integração fica atrás de uma porta (`Geocodificador`), com o adaptador da
Geoapify em `backend/infra/geoapify.py`; os testes usam um geocodificador
falso, então rodam sem internet e sem chave. Erros da API viram mensagens
claras (chave recusada, limite atingido, sem conexão) e a chave nunca aparece
em mensagem de erro.

## Estrutura de pastas — backend, frontend e testes bem separados

```
quadrante-python/
├── app.py                     # ÚNICO ponto de contato entre backend e frontend:
│                                monta as rotas Flask, aponta pros templates/static
│                                do frontend/ e chama os serviços do backend/
├── requirements.txt
├── .env.example               modelo de configuração (copie para .env)
├── README.md
│
├── backend/                   # TUDO que é lógica — zero HTML/CSS/JS aqui dentro
│   ├── config.py                leitura do .env e das variáveis de ambiente
│   ├── infra/                   adaptador da API de geocodificação (Geoapify)
│   ├── domain/                  entidades puras: Fiscal, Condominio, Ausencia,
│   │                            Realocacao, Rota, GeoPonto, AtribuicaoSugerida
│   ├── estruturas/              Vetor, ListaEncadeada, Pilha, Fila — implementadas
│   │                            do zero (sem list.append/pop, sem collections.deque)
│   ├── repository/              Store in-memory — usa as estruturas acima como
│   │                            containers REAIS do estado do sistema
│   ├── service/                 os 3 algoritmos:
│   │   ├── routing_service.py       TSP (nearest-neighbor + 2-opt)
│   │   ├── clustering_service.py    k-means geográfico + rebalanceamento
│   │   ├── cadastro_service.py      geocodifica o endereço e escolhe o fiscal mais próximo
│   │   └── reallocation_service.py  alocação gulosa + fila/pilha de negócio
│   └── seed/                    dados.json real (Maceió-AL) + loader
│
├── frontend/                  # TUDO que é apresentação — zero lógica de negócio aqui
│   ├── templates/index.html     página única (console de despacho), responsiva
│   └── static/
│       ├── css/                 tokens.css (paleta, tipografia, espaçamento),
│       │                        base.css, componentes.css, layout.css
│       ├── js/
│       │   ├── app.js               ponto de entrada (ES modules, sem build)
│       │   └── modulos/             api, estado, mapa, painéis (equipe, rota,
│       │                            ausências, histórico, k-means), toasts,
│       │                            diálogo de confirmação, abas acessíveis
│       ├── fonts/               IBM Plex Sans e Mono (self-hosted)
│       └── vendor/              Leaflet 1.9.4 e markercluster 1.5.3 locais (sem CDN)
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

HTML, CSS e JavaScript puros (ES modules, sem framework e sem build step —
sobe direto do Flask). Leaflet, markercluster e as fontes são servidos
localmente; só os tiles do mapa (CARTO Voyager, com fallback para
OpenStreetMap) dependem de internet, e a interface avisa quando eles não
carregam.

**Mapa:** cada condomínio é um pin em gota na cor do fiscal; pins próximos
se agrupam em círculos com contagem e se abrem ao aproximar. O mapa base
mostra os nomes das ruas; o popup mostra nome e endereço. Na rota, os pins
são numerados na ordem de visita e ganham o nome ao lado a partir do zoom 15.
O botão no canto superior direito troca o mapa base.

**Layout:** console de despacho em três colunas no desktop — equipe à
esquerda, mapa ao centro, operações à direita em abas (Rota, Ausências,
Histórico, K-means, Novo). Em telas estreitas vira uma coluna: fiscais em faixa
horizontal, mapa e abas empilhados.

**Decisões de UX:**

- A cor de cada fiscal é a mesma na lista, no mapa, nas rotas e nas tabelas.
  Passar o mouse (ou focar com o teclado) num fiscal isola a carteira dele
  no mapa; clicar mostra a rota otimizada e a ordem das visitas, e clicar
  numa parada centraliza o mapa nela. `Esc` volta ao mapa geral.
- Fila e Pilha são desenhadas como a estrutura que são: a Fila horizontal
  (sai pela frente, entra pelo fim, "próxima a atender" em destaque) e a
  Pilha vertical (topo em destaque, "próxima a desfazer").
- Cada painel mostra a estrutura de dados usada e sua complexidade, e um
  bloco recolhível explica por que ela foi escolhida.
- Feedback em toda ação: botão em carregamento, toast de sucesso ou erro,
  contadores nas abas, estados vazios que dizem o próximo passo. Ações
  impossíveis ficam desabilitadas (processar com a fila vazia, desfazer sem
  realocação ativa) e ações irreversíveis (aplicar k-means, reiniciar)
  pedem confirmação.
- Velocidade visível: o topo mostra a latência da última requisição, cada
  rota e cada sugestão mostram o tempo de resposta, e rotas já calculadas
  vêm do cache do navegador até o estado mudar.
- Acessibilidade: contraste WCAG AA, foco visível, abas com navegação por
  setas, `aria-live` nos resultados, alvos de toque de 44 px em telas de
  toque e respeito a `prefers-reduced-motion`.

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
3. **Demo ao vivo (3-4 min):** abrir a página, mostrar o mapa geral, passar
   o mouse num fiscal (isola a carteira), clicar nele (rota otimizada e
   tempo de resposta no topo), registrar uma ausência (a Fila cresce e a
   aba ganha contador), processar a fila (realocação, mapa e contagens
   atualizam), abrir o Histórico e desfazer (a Pilha reage), rodar o
   k-means, clicar num condomínio da tabela para achá-lo no mapa e aplicar
   a sugestão.
4. **Fechamento (30s):** essa é uma versão real de produção da empresa do
   apresentador — os dados geográficos são reais, os algoritmos são os
   mesmos que já rodam em produção; o que mudou pra caber na disciplina foi
   a persistência (agora em memória, sobre as quatro estruturas) e a
   ausência de HTTP/auth de produção.

## Dados

`backend/seed/dados.json`: nomes de fiscais e condomínios são fictícios; as
coordenadas correspondem a pontos reais de Maceió-AL, usadas como massa de
teste geográfica (geocodificação falsa não plota certo no mapa).
