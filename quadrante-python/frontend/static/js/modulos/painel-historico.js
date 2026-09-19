import { desfazerUltima, humanizarErro, reverterExpiradas } from "./acoes.js";
import { atualizarContador, estadoVazio } from "./componentes.js";
import { corDoFiscal } from "./cores.js";
import { comCarregando, desabilitar, el, estaDesabilitado } from "./dom.js";
import { assinar, estado, fiscalPorId } from "./estado.js";
import { distancia, nomeProprio } from "./formatacao.js";
import { notificar } from "./notificacoes.js";

const LIMITE_VISIVEL = 10;
const campo = (id) => document.getElementById(id);

function cartaoDaPilha(realocacao, indice, topoAtivo) {
  const destaque = indice === topoAtivo;
  const cor = corDoFiscal(fiscalPorId(realocacao.para));
  return el(
    "li",
    {
      class: `cartao-ed${destaque ? " destaque" : ""}${realocacao.ativa ? "" : " revertida"}`,
      estilo: { "--cor-para": cor },
    },
    destaque ? el("span", { class: "rotulo-topo" }, "topo · próxima a desfazer") : null,
    el("strong", {}, nomeProprio(realocacao.condominio_nome)),
    el("span", { class: "fluxo" }, el("b", {}, nomeProprio(realocacao.de_nome)), "→", el("b", {}, nomeProprio(realocacao.para_nome))),
    el(
      "span",
      { class: "meta-linha" },
      el("span", { class: `tag ${realocacao.ativa ? "tag-ok" : "tag-neutra"}` }, realocacao.ativa ? "ativa" : "revertida"),
      el("span", {}, distancia(realocacao.distancia_m)),
    ),
  );
}

function renderizar() {
  const alvo = campo("historico");
  const historico = estado.historico;
  const ativas = historico.filter((r) => r.ativa).length;
  atualizarContador("contador-historico", ativas);
  desabilitar(campo("btn-desfazer"), ativas === 0, "Não há realocação ativa para desfazer");

  if (historico.length === 0) {
    alvo.replaceChildren(
      estadoVazio({
        nomeIcone: "pilha",
        titulo: "Nenhuma realocação ainda",
        texto: "Processe uma solicitação da fila ou aplique a redistribuição do k-means. Cada mudança empilha aqui.",
      }),
    );
    return;
  }

  const topoAtivo = historico.findIndex((r) => r.ativa);
  const visiveis = historico.slice(0, LIMITE_VISIVEL);
  const restantes = historico.length - visiveis.length;

  alvo.replaceChildren(
    el("ol", { class: "pilha", "aria-label": "Realocações, da mais recente para a mais antiga" }, visiveis.map((r, i) => cartaoDaPilha(r, i, topoAtivo))),
    restantes > 0 ? el("p", { class: "nota-tabela" }, `+ ${restantes} realocações mais antigas na pilha`) : null,
  );
}

async function aoDesfazer() {
  const botao = campo("btn-desfazer");
  if (estaDesabilitado(botao)) return;
  await comCarregando(botao, async () => {
    try {
      await desfazerUltima();
    } catch (erro) {
      notificar.erro("Não foi possível desfazer", humanizarErro(erro.message));
    }
  });
}

async function aoReverter() {
  await comCarregando(campo("btn-reverter-expiradas"), async () => {
    try {
      await reverterExpiradas();
    } catch (erro) {
      notificar.erro("Não foi possível reverter", humanizarErro(erro.message));
    }
  });
}

export function iniciarHistorico() {
  renderizar();
  assinar("historico", renderizar);
  campo("btn-desfazer").addEventListener("click", aoDesfazer);
  campo("btn-reverter-expiradas").addEventListener("click", aoReverter);
}
