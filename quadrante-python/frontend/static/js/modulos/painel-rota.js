import { estadoVazio, marcaDeFiscal } from "./componentes.js";
import { corDoFiscal } from "./cores.js";
import { el, esqueletos } from "./dom.js";
import { assinar, estado, fiscalPorId } from "./estado.js";
import { enderecoCurto, nomeProprio, plural, quilometros } from "./formatacao.js";
import { focarParada, realcarParada } from "./mapa.js";

const conteudo = () => document.getElementById("rota-conteudo");

function estatistica(valor, rotulo, unidade) {
  return el(
    "div",
    { class: "estatistica" },
    el("strong", {}, valor, unidade ? el("small", {}, ` ${unidade}`) : null),
    el("span", {}, rotulo),
  );
}

function linhaDaParada(parada, cor) {
  return el(
    "li",
    {},
    el(
      "button",
      {
        type: "button",
        class: "parada",
        title: "Mostrar no mapa",
        onclick: () => focarParada(parada.ordem),
        onmouseenter: () => realcarParada(parada.ordem, true),
        onmouseleave: () => realcarParada(parada.ordem, false),
        onfocus: () => realcarParada(parada.ordem, true),
        onblur: () => realcarParada(parada.ordem, false),
      },
      el("span", { class: "parada-num", estilo: { "--cor": cor } }, parada.ordem),
      el(
        "span",
        { class: "parada-info" },
        el("span", { class: "parada-nome" }, nomeProprio(parada.condominio_nome)),
        parada.endereco ? el("span", { class: "parada-endereco" }, enderecoCurto(parada.endereco)) : null,
      ),
      parada.ordem === 1 ? el("span", { class: "tag tag-neutra" }, "início") : null,
    ),
  );
}

function renderizar() {
  const alvo = conteudo();
  const fiscal = fiscalPorId(estado.selecionadoId);

  if (!fiscal) {
    alvo.replaceChildren(
      estadoVazio({
        nomeIcone: "rota",
        titulo: "Nenhum fiscal selecionado",
        texto: "Escolha um fiscal na lista para ver a rota otimizada e a ordem das visitas.",
      }),
    );
    return;
  }

  if (fiscal.papel === "coordenador") {
    alvo.replaceChildren(
      estadoVazio({
        nomeIcone: "usuarios",
        titulo: `${nomeProprio(fiscal.nome)} é coordenador`,
        texto: `Carteira fixa de ${plural(fiscal.qtd_condominios, "condomínio", "condomínios")}: não entra em rota nem em realocação.`,
      }),
    );
    return;
  }

  if (estado.carregandoRota || !estado.rota) {
    alvo.replaceChildren(
      el("div", { class: "estatisticas" }, ...esqueletos(2, "fiscal-esqueleto")),
      el("div", { class: "paradas" }, ...esqueletos(5, "fiscal-esqueleto")),
    );
    return;
  }

  const cor = corDoFiscal(fiscal);
  const paradas = estado.rota.paradas.filter((p) => p.latitude != null && p.longitude != null);

  alvo.replaceChildren(
    el("div", { class: "rota-titulo" }, marcaDeFiscal(cor), el("h2", {}, nomeProprio(fiscal.nome))),
    el(
      "div",
      { class: "estatisticas" },
      estatistica(quilometros(estado.rota.distancia_total_km), "percurso total", "km"),
      estatistica(paradas.length, "paradas", ""),
    ),
    el("h3", { class: "subtitulo" }, "Ordem das visitas"),
    el("ol", { class: "paradas", "aria-label": "Paradas da rota, na ordem otimizada" }, paradas.map((p) => linhaDaParada(p, cor))),
  );
}

export function iniciarRota() {
  renderizar();
  assinar("rota", renderizar);
}
