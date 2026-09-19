# Quadrante — guia para agentes

Projeto da disciplina de Estruturas de Dados. Apresentação: **28/09/2026**. O professor valoriza UX/UI, modelagem de dados e tempo de resposta. Roteirização e divisão territorial de fiscais de campo entre condomínios de Maceió-AL.

## Regras do dono (Viny)

- Responder sempre em português do Brasil, direto e sem enrolação.
- Código sem nenhum comentário (`#`, `//`, docstrings novos). Tipagem estrita quando a linguagem permitir.
- Ao editar arquivos, resumir a mudança em vez de colar o código no chat.
- Só gerar documentos se pedirem. Nunca commitar sem pedido explícito.
- Postura de AppSec: validar entrada, sem SQL concatenado, sem segredo no código, menor privilégio.
- Não editar `C:\Dev\RotasAGE` (sistema de produção, só referência).

## Rodar

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
pytest
```

Só Flask e pytest como dependências. Estado atual: 57 testes passando.

## Arquitetura

- `app.py`: única peça que conhece backend e frontend. Só monta rotas.
- `backend/domain`: entidades puras. `backend/estruturas`: Vetor, ListaEncadeada, Pilha e Fila **feitas à mão** (proibido trocar por `list.append/pop` como caixa-preta ou `collections.deque`). `backend/repository/store.py`: usa as 4 estruturas como containers reais. `backend/service`: TSP (vizinho mais próximo + 2-opt), k-means geográfico com rebalanceamento, alocação gulosa, cadastro por endereço. `backend/infra`: adaptador da Geoapify. `backend/config.py`: leitura do `.env`.
- `frontend/`: HTML, CSS e ES modules sem build. Leaflet 1.9.4 e markercluster 1.5.3 locais em `static/vendor`, fontes IBM Plex locais. Nenhuma lógica de negócio no JS.
- Backend nunca importa de frontend. Dependências apontam para dentro (domínio não conhece infra).

## Configuração e API de localização

`.env` (nunca versionado; existe `.env.example`): `QUADRANTE_HOST`, `QUADRANTE_PORT`, `QUADRANTE_DEBUG`, `GEOAPIFY_API_KEY`. `DEBUG=1` só com host `127.0.0.1`.

A chave da Geoapify é usada no servidor (geocodificação, `GET /api/geocodificar` e `POST /api/condominios`, aba "Novo") e no navegador (tiles com nomes de bairro). Sem chave ou com chave inválida o mapa cai para CARTO e depois OpenStreetMap, e a aba "Novo" avisa. Nunca logar nem devolver a chave em mensagem de erro.

## Dados

`backend/seed/dados.json`: nomes de fiscais e condomínios fictícios, endereços e coordenadas reais de Maceió (127 condomínios, 6 fiscais de campo, 3 coordenadores). Não trocar por dados falsos: geocodificação depende de endereço real.

## Pendente

1. **Testar com a chave real da Geoapify**: nomes de bairro no mapa base e busca de endereço na aba "Novo". Tudo foi validado só com API e tiles falsos. O contrato da resposta (`results[].lat/lon/formatted/suburb`) veio da documentação.
2. Revisar `git status` e commitar (a pasta `estruturas-dados-python/` foi removida de propósito; há arquivos novos não versionados).
3. Desequilíbrio do k-means: o Marcos fica com ~3 condomínios contra 19 a 25 dos outros após a sugestão. Investigar se é o rebalanceamento ou o centroide inicial.
4. Modelagem de dados (o professor valora): DER, índices e justificativa de cada estrutura. Sem banco de dados por decisão do dono; o Store é em memória.

## Como verificar antes de dizer que terminou

- `pytest` verde.
- Abrir a aplicação e conferir: mapa geral com pins e clusters, hover num fiscal isola a carteira, rota com pins numerados, aba "Novo" (buscar, escolher candidato, cadastrar), Ausências (fila), Histórico (pilha, desfazer), K-means (aplicar), Reiniciar demonstração.
- Console do navegador sem erros e sem violações de acessibilidade (axe) em todas as abas; layout ok em 1280, 820 e 390 px.
- Cuidado ao redesenhar o mapa geral: `fitBounds` animado sobrescreve `setView` feito logo depois (por isso o enquadramento do mapa geral não é animado).
