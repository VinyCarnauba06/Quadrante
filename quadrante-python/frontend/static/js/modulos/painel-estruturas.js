import { api } from "./api.js";
import { enfileirarAusencia, processarProxima, desfazerUltima } from "./acoes.js";
import { assinar, estado } from "./estado.js";
import { notificar } from "./notificacoes.js";

function renderizarVetor(vetor, container) {
  container.replaceChildren();
  const elTamanho = document.getElementById("vetor-tamanho");
  const elCapacidade = document.getElementById("vetor-capacidade");
  if (elTamanho) elTamanho.textContent = `${vetor.tamanho} fiscais`;
  if (elCapacidade) elCapacidade.textContent = `${vetor.capacidade} posições`;

  vetor.elementos.forEach((elem, idx) => {
    const item = document.createElement("div");
    item.className = "item-vetor";
    const spanIdx = document.createElement("span");
    spanIdx.className = "item-vetor-idx";
    spanIdx.textContent = `[${idx}]`;
    const spanNome = document.createElement("span");
    spanNome.textContent = elem.nome.split(" ")[0];
    item.append(spanIdx, spanNome);
    container.append(item);
  });

  const vazios = vetor.capacidade - vetor.tamanho;
  for (let i = 0; i < vazios; i++) {
    const idx = vetor.tamanho + i;
    const item = document.createElement("div");
    item.className = "item-vetor item-vetor-vazio";
    item.textContent = `[${idx}] vazio`;
    container.append(item);
  }
}

function renderizarLista(lista, container) {
  container.replaceChildren();
  const elNome = document.getElementById("lista-fiscal-nome");
  const elTamanho = document.getElementById("lista-tamanho");
  if (elNome) elNome.textContent = lista.fiscal ? lista.fiscal.nome : "Nenhum";
  if (elTamanho) elTamanho.textContent = `${lista.tamanho} nós`;

  if (lista.elementos.length === 0) {
    const vazio = document.createElement("p");
    vazio.className = "texto-suave";
    vazio.textContent = "Carteira vazia (cabeça -> None).";
    container.append(vazio);
    return;
  }

  lista.elementos.forEach((cond, idx) => {
    const no = document.createElement("div");
    no.className = "no-lista";

    const bloco = document.createElement("div");
    bloco.className = "no-bloco";
    bloco.textContent = cond.nome;

    const seta = document.createElement("span");
    seta.className = "no-seta";
    seta.textContent = idx === lista.elementos.length - 1 ? "➔ None" : "➔";

    no.append(bloco, seta);
    container.append(no);
  });
}

function renderizarFila(fila, container) {
  container.replaceChildren();
  const elTamanho = document.getElementById("fila-tamanho");
  const elProximo = document.getElementById("fila-proximo");
  if (elTamanho) elTamanho.textContent = `${fila.tamanho} solicitação(ões)`;
  if (elProximo) {
    elProximo.textContent = fila.cabeca ? fila.cabeca.fiscal_nome : "Nenhum";
  }

  if (fila.elementos.length === 0) {
    const vazio = document.createElement("p");
    vazio.className = "texto-suave";
    vazio.textContent = "Fila vazia. Nenhuma ausência aguardando.";
    container.append(vazio);
    return;
  }

  fila.elementos.forEach((s, idx) => {
    const item = document.createElement("div");
    item.className = "item-fila";
    if (idx === 0) item.classList.add("item-fila-frente");

    const rotulo = document.createElement("span");
    rotulo.textContent = `${idx === 0 ? "FRENTE: " : `${idx + 1}º: `}${s.fiscal_nome} (${s.motivo})`;

    item.append(rotulo);
    container.append(item);
  });
}

function renderizarPilha(pilha, container) {
  container.replaceChildren();
  const elTamanho = document.getElementById("pilha-tamanho");
  const elTopo = document.getElementById("pilha-topo");
  if (elTamanho) elTamanho.textContent = `${pilha.tamanho} registro(s)`;
  if (elTopo) {
    elTopo.textContent = pilha.topo ? `${pilha.topo.condominio_nome}` : "Nenhum";
  }

  if (pilha.elementos.length === 0) {
    const vazio = document.createElement("p");
    vazio.className = "texto-suave";
    vazio.textContent = "Pilha vazia. Nenhuma realocação realizada.";
    container.append(vazio);
    return;
  }

  pilha.elementos.forEach((r, idx) => {
    const item = document.createElement("div");
    item.className = "item-pilha";
    if (idx === 0) item.classList.add("item-pilha-topo");

    const rotulo = document.createElement("span");
    rotulo.textContent = `${idx === 0 ? "TOPO: " : ""}${r.condominio_nome} (${r.de} ➔ ${r.para})`;

    item.append(rotulo);
    container.append(item);
  });
}

export async function carregarDadosEstruturas() {
  const containerVetor = document.getElementById("visualizacao-vetor");
  const containerLista = document.getElementById("visualizacao-lista");
  const containerFila = document.getElementById("visualizacao-fila");
  const containerPilha = document.getElementById("visualizacao-pilha");

  const url = estado.selecionadoId
    ? `/api/estruturas/raio-x?fiscal_id=${encodeURIComponent(estado.selecionadoId)}`
    : "/api/estruturas/raio-x";

  try {
    const dados = await api.get(url);
    if (containerVetor) renderizarVetor(dados.vetor, containerVetor);
    if (containerLista) renderizarLista(dados.lista_encadeada, containerLista);
    if (containerFila) renderizarFila(dados.fila, containerFila);
    if (containerPilha) renderizarPilha(dados.pilha, containerPilha);
  } catch (erro) {
    notificar.erro("Erro ao carregar estruturas", erro.message);
  }
}

function esperar(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function executarModoDemo(botao) {
  botao.disabled = true;
  const textoOriginal = botao.innerHTML;
  botao.textContent = "Executando simulação...";

  try {
    notificar.info("Simulação Didática (1/4)", "1. Enfileirando solicitação de ausência na Fila FIFO...");
    const hoje = new Date().toISOString().slice(0, 10);
    await enfileirarAusencia({
      fiscal_id: "fisc-002",
      motivo: "saude",
      data_inicio: hoje,
      data_fim: hoje,
    });
    await carregarDadosEstruturas();
    await esperar(2000);

    notificar.info("Simulação Didática (2/4)", "2. Processando cabeça da Fila FIFO e redistribuindo na Lista Encadeada...");
    await processarProxima();
    await carregarDadosEstruturas();
    await esperar(2500);

    notificar.info("Simulação Didática (3/4)", "3. Desfazendo última ação no Topo da Pilha LIFO...");
    await desfazerUltima();
    await carregarDadosEstruturas();
    await esperar(2000);

    notificar.ok("Simulação Didática (4/4)", "4. Medindo latência das operações no console...");
    if (window.quadrante && window.quadrante.benchmark) {
      await window.quadrante.benchmark();
    }
  } catch (erro) {
    notificar.erro("Falha na simulação", erro.message);
  } finally {
    botao.disabled = false;
    botao.innerHTML = textoOriginal;
  }
}

export function iniciarPainelEstruturas() {
  const modal = document.getElementById("modal-estruturas");
  const btnAbrir = document.getElementById("btn-abrir-estruturas");
  const btnFechar = document.getElementById("btn-fechar-estruturas");
  const btnAtualizar = document.getElementById("btn-atualizar-estruturas");
  const btnModoDemo = document.getElementById("btn-modo-demo");

  if (!modal || !btnAbrir) return;

  btnAbrir.addEventListener("click", () => {
    carregarDadosEstruturas();
    modal.showModal();
  });

  if (btnFechar) {
    btnFechar.addEventListener("click", () => modal.close());
  }

  if (btnAtualizar) {
    btnAtualizar.addEventListener("click", carregarDadosEstruturas);
  }

  if (btnModoDemo) {
    btnModoDemo.addEventListener("click", () => executarModoDemo(btnModoDemo));
  }

  assinar("selecao", () => {
    if (modal.open) carregarDadosEstruturas();
  });

  assinar("fila", () => {
    if (modal.open) carregarDadosEstruturas();
  });

  assinar("historico", () => {
    if (modal.open) carregarDadosEstruturas();
  });
}
