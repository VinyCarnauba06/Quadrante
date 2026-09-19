import { enfileirarAusencia, humanizarErro, processarProxima } from "./acoes.js";
import { atualizarContador, estadoVazio } from "./componentes.js";
import { comCarregando, desabilitar, el, estaDesabilitado } from "./dom.js";
import { assinar, estado, fiscaisDeCampo } from "./estado.js";
import { dataCurta, dataParaCampo, nomeProprio, rotuloMotivo } from "./formatacao.js";
import { icone } from "./icones.js";
import { notificar } from "./notificacoes.js";

const campo = (id) => document.getElementById(id);

function definirDatasPadrao() {
  const hoje = new Date();
  const fim = new Date(hoje);
  fim.setDate(fim.getDate() + 6);
  campo("ausencia-inicio").value = dataParaCampo(hoje);
  campo("ausencia-fim").value = dataParaCampo(fim);
  campo("ausencia-fim").min = campo("ausencia-inicio").value;
  mostrarErroDePeriodo("");
}

function mostrarErroDePeriodo(mensagem) {
  const erro = campo("erro-periodo");
  erro.textContent = mensagem;
  erro.hidden = mensagem === "";
  campo("ausencia-fim").setAttribute("aria-invalid", String(mensagem !== ""));
}

function validarPeriodo() {
  const inicio = campo("ausencia-inicio").value;
  const fim = campo("ausencia-fim").value;
  if (!inicio || !fim) {
    mostrarErroDePeriodo("Informe a data de início e a data de fim.");
    return false;
  }
  if (fim < inicio) {
    mostrarErroDePeriodo("A data de fim não pode ser anterior à de início.");
    return false;
  }
  mostrarErroDePeriodo("");
  return true;
}

function preencherFiscais() {
  const select = campo("ausencia-fiscal");
  const anterior = select.value;
  select.replaceChildren(
    ...fiscaisDeCampo().map((f) => el("option", { value: f.id }, nomeProprio(f.nome))),
  );
  if (anterior && [...select.options].some((o) => o.value === anterior)) select.value = anterior;
}

function cartaoDaFila(solicitacao, indice) {
  const primeiro = indice === 0;
  return el(
    "div",
    { class: `cartao-ed${primeiro ? " destaque" : ""}`, role: "listitem" },
    primeiro ? el("span", { class: "rotulo-topo" }, "próxima a atender") : null,
    el("span", { class: "periodo" }, `#${indice + 1}`),
    el("strong", {}, nomeProprio(solicitacao.fiscal_nome)),
    el("span", { class: "tag" }, rotuloMotivo(solicitacao.motivo)),
    el("span", { class: "periodo" }, `${dataCurta(solicitacao.data_inicio)} → ${dataCurta(solicitacao.data_fim)}`),
  );
}

function renderizarFila() {
  const alvo = campo("fila-ausencias");
  const fila = estado.fila;
  atualizarContador("contador-fila", fila.length);
  desabilitar(campo("btn-processar-fila"), fila.length === 0, "A fila está vazia");

  if (fila.length === 0) {
    alvo.replaceChildren(
      estadoVazio({
        nomeIcone: "fila",
        titulo: "Fila vazia",
        texto: "Registre uma ausência acima. A solicitação entra no fim da fila e é atendida na ordem de chegada.",
      }),
    );
    return;
  }

  const itens = fila.flatMap((s, i) => {
    const cartao = cartaoDaFila(s, i);
    return i < fila.length - 1 ? [cartao, el("span", { class: "fila-seta", "aria-hidden": "true" }, icone("seta"))] : [cartao];
  });

  alvo.replaceChildren(
    el("div", { class: "fila rolagem-fina", role: "list", "aria-label": "Fila de solicitações, da frente para o fim" }, itens),
    el("div", { class: "legenda-ed", "aria-hidden": "true" }, el("span", {}, "← sai primeiro"), el("span", {}, "entra por último →")),
  );
}

async function aoEnviar(evento) {
  evento.preventDefault();
  if (!validarPeriodo()) {
    campo("ausencia-fim").focus();
    return;
  }
  const botao = campo("btn-enfileirar");
  await comCarregando(botao, async () => {
    try {
      await enfileirarAusencia({
        fiscal_id: campo("ausencia-fiscal").value,
        motivo: campo("ausencia-motivo").value,
        data_inicio: campo("ausencia-inicio").value,
        data_fim: campo("ausencia-fim").value,
      });
    } catch (erro) {
      notificar.erro("Não foi possível enfileirar", humanizarErro(erro.message));
    }
  });
}

async function aoProcessar() {
  const botao = campo("btn-processar-fila");
  if (estaDesabilitado(botao)) return;
  await comCarregando(botao, async () => {
    try {
      await processarProxima();
    } catch (erro) {
      notificar.erro("Não foi possível processar a solicitação", erro.message);
    }
  });
}

export function iniciarAusencias() {
  definirDatasPadrao();
  renderizarFila();
  assinar("fiscais", preencherFiscais);
  assinar("fila", renderizarFila);
  assinar("reinicio", definirDatasPadrao);

  campo("ausencia-inicio").addEventListener("change", () => {
    campo("ausencia-fim").min = campo("ausencia-inicio").value;
    if (campo("ausencia-fim").value && campo("ausencia-fim").value < campo("ausencia-inicio").value) {
      campo("ausencia-fim").value = campo("ausencia-inicio").value;
    }
    validarPeriodo();
  });
  campo("ausencia-fim").addEventListener("change", validarPeriodo);
  campo("form-ausencia").addEventListener("submit", aoEnviar);
  campo("btn-processar-fila").addEventListener("click", aoProcessar);
}
