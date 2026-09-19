import { abrirAba } from "./tabs.js";
import { marcaDeFiscal } from "./componentes.js";
import { corDoFiscal } from "./cores.js";
import { el, esqueletos } from "./dom.js";
import { assinar, estado, fiscaisDeCampo, fiscalPorId } from "./estado.js";
import { nomeProprio, plural } from "./formatacao.js";
import { destacarFiscal } from "./mapa.js";
import { selecionar } from "./servicos.js";

const lista = () => document.getElementById("lista-fiscais");

function idParaDestaque() {
  const fiscal = fiscalPorId(estado.selecionadoId);
  return fiscal && fiscal.papel === "coordenador" ? fiscal.id : null;
}

function alternarSelecao(fiscal) {
  const jaSelecionado = estado.selecionadoId === fiscal.id;
  selecionar(jaSelecionado ? null : fiscal.id);
  if (!jaSelecionado && fiscal.papel === "fiscal_campo") abrirAba("rota");
}

function itemDoFiscal(fiscal, maximo) {
  const coordenador = fiscal.papel === "coordenador";
  const percentual = Math.min(100, (fiscal.qtd_condominios / maximo) * 100);
  return el(
    "li",
    {},
    el(
      "button",
      {
        type: "button",
        class: "fiscal",
        "data-id": fiscal.id,
        "aria-pressed": String(estado.selecionadoId === fiscal.id),
        title: coordenador ? "Coordenador: ver carteira no mapa" : "Ver rota otimizada",
        estilo: { "--cor": corDoFiscal(fiscal), "--pct": `${percentual}%` },
        onclick: () => alternarSelecao(fiscal),
        onmouseenter: () => destacarFiscal(fiscal.id),
        onmouseleave: () => destacarFiscal(idParaDestaque()),
        onfocus: () => destacarFiscal(fiscal.id),
        onblur: () => destacarFiscal(idParaDestaque()),
      },
      marcaDeFiscal(corDoFiscal(fiscal)),
      el(
        "span",
        { class: "fiscal-nome" },
        nomeProprio(fiscal.nome),
        el("span", { class: "fiscal-papel" }, coordenador ? "Coordenador" : "Fiscal de campo"),
      ),
      el(
        "span",
        { class: "fiscal-carga" },
        el("span", { class: "fiscal-num", "aria-label": plural(fiscal.qtd_condominios, "condomínio", "condomínios") }, fiscal.qtd_condominios),
        el("span", { class: "fiscal-barra", "aria-hidden": "true" }, el("span")),
      ),
    ),
  );
}

function renderizar() {
  if (estado.fiscais.length === 0) return;
  const focado = document.activeElement?.dataset?.id;
  const maximo = Math.max(1, ...estado.fiscais.map((f) => f.qtd_condominios));
  lista().replaceChildren(...estado.fiscais.map((f) => itemDoFiscal(f, maximo)));
  if (focado) lista().querySelector(`[data-id="${CSS.escape(focado)}"]`)?.focus({ preventScroll: true });

  const total = estado.fiscais.reduce((soma, f) => soma + f.qtd_condominios, 0);
  const coordenadores = estado.fiscais.length - fiscaisDeCampo().length;
  document.getElementById("resumo-equipe").textContent = `${plural(fiscaisDeCampo().length, "fiscal de campo", "fiscais de campo")} · ${plural(coordenadores, "coordenador", "coordenadores")} · ${plural(total, "condomínio", "condomínios")}`;
}

function atualizarSelecao() {
  lista()
    .querySelectorAll(".fiscal")
    .forEach((botao) => botao.setAttribute("aria-pressed", String(botao.dataset.id === estado.selecionadoId)));
}

export function mostrarEsqueleto() {
  lista().replaceChildren(...esqueletos(6).map((no) => el("li", {}, no)));
}

export function mostrarFalhaDeCarga(aoTentarNovamente) {
  document.getElementById("resumo-equipe").textContent = "Não foi possível carregar a equipe.";
  lista().replaceChildren(
    el(
      "li",
      {},
      el("button", { type: "button", class: "btn btn-bloco", onclick: aoTentarNovamente }, "Tentar novamente"),
    ),
  );
}

export function iniciarEquipe() {
  mostrarEsqueleto();
  assinar("fiscais", renderizar);
  assinar("selecao", atualizarSelecao);
}
