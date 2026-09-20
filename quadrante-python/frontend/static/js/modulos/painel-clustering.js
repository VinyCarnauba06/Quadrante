import { aplicarSugestao, calcularSugestao, humanizarErro } from "./acoes.js";
import { estadoVazio, marcaDeFiscal } from "./componentes.js";
import { corDoFiscal } from "./cores.js";
import { confirmar } from "./dialogo.js";
import { comCarregando, el } from "./dom.js";
import { assinar, estado, fiscalPorId, fiscalPorNome } from "./estado.js";
import { nomeProprio, plural } from "./formatacao.js";
import { icone } from "./icones.js";
import { focarCondominio } from "./mapa.js";
import { notificar } from "./notificacoes.js";
import { selecionar } from "./servicos.js";

const resultado = () => document.getElementById("resultado-clustering");
const layoutEmpilhado = window.matchMedia("(max-width: 980px)");

async function verNoMapa(condominioId) {
  if (estado.selecionadoId !== null) await selecionar(null);
  if (focarCondominio(condominioId) && layoutEmpilhado.matches) {
    document.getElementById("palco").scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function celulaDeFiscal(nome) {
  const cor = corDoFiscal(fiscalPorNome(nome));
  return el("span", { class: "celula-fiscal" }, marcaDeFiscal(cor), nomeProprio(nome));
}

function linhaDaMudanca(mudanca) {
  return el(
    "tr",
    {},
    el(
      "td",
      {},
      el(
        "button",
        { type: "button", class: "link-mapa", title: "Mostrar no mapa", onclick: () => verNoMapa(mudanca.condominio_id) },
        nomeProprio(mudanca.condominio_nome),
      ),
    ),
    el("td", {}, celulaDeFiscal(mudanca.fiscal_atual_nome)),
    el("td", {}, celulaDeFiscal(mudanca.fiscal_sugerido_nome)),
  );
}

function zonas(sugestao) {
  const entradas = Object.entries(sugestao.tamanho_por_zona).sort((a, b) => b[1] - a[1]);
  const maximo = Math.max(1, ...entradas.map(([, qtd]) => qtd));
  return el(
    "div",
    { class: "zonas", role: "list", "aria-label": "Condomínios por zona após a sugestão" },
    entradas.map(([nome, qtd]) => {
      const cor = corDoFiscal(fiscalPorNome(nome));
      return el(
        "div",
        { class: "zona", role: "listitem", estilo: { "--cor": cor, "--pct": `${(qtd / maximo) * 100}%` } },
        marcaDeFiscal(cor),
        el("span", { class: "zona-nome" }, nomeProprio(nome)),
        el("span", { class: "zona-qtd" }, qtd),
        el("div", { class: "zona-barra", "aria-hidden": "true" }, el("span")),
      );
    }),
  );
}

function estatistica(valor, rotulo) {
  return el("div", { class: "estatistica" }, el("strong", {}, valor), el("span", {}, rotulo));
}

async function aoAplicar(botao) {
  const total = estado.sugestao.total_mudancas;
  const confirmado = await confirmar({
    titulo: `Aplicar ${plural(total, "mudança", "mudanças")}?`,
    texto: `${plural(total, "condomínio troca", "condomínios trocam")} de fiscal de forma definitiva. Essa ação não entra no histórico, então o botão Desfazer não a reverte. Só "Reiniciar demonstração" volta ao estado inicial.`,
    rotuloConfirmar: `Aplicar ${total}`,
  });
  if (!confirmado) return;
  await comCarregando(botao, async () => {
    try {
      await aplicarSugestao();
    } catch (erro) {
      notificar.erro("Não foi possível aplicar a sugestão", humanizarErro(erro.message));
    }
  });
}

function renderizar() {
  const alvo = resultado();
  const sugestao = estado.sugestao;

  if (estado.aplicacaoClustering !== null) {
    alvo.replaceChildren(
      el(
        "div",
        { class: "acoes-empilhadas" },
        estadoVazio({
          nomeIcone: "check",
          titulo: "Sugestão aplicada",
          texto: `${plural(estado.aplicacaoClustering, "condomínio reatribuído", "condomínios reatribuídos")}. Calcule de novo para ver se ainda restam ajustes.`,
        }),
      ),
    );
    return;
  }

  if (!sugestao) {
    alvo.replaceChildren();
    return;
  }

  if (sugestao.total_mudancas === 0) {
    alvo.replaceChildren(
      el(
        "div",
        { class: "acoes-empilhadas" },
        estadoVazio({
          nomeIcone: "check",
          titulo: "Distribuição já está equilibrada",
          texto: `${plural(sugestao.total_condominios, "condomínio avaliado", "condomínios avaliados")}. Nenhuma troca sugerida.`,
        }),
      ),
    );
    return;
  }

  const botaoAplicar = el(
    "button",
    { type: "button", class: "btn btn-primario btn-bloco", id: "btn-aplicar-clustering" },
    icone("check"),
    `Aplicar ${plural(sugestao.total_mudancas, "mudança", "mudanças")}`,
  );
  botaoAplicar.addEventListener("click", () => aoAplicar(botaoAplicar));

  alvo.replaceChildren(
    el(
      "div",
      { class: "acoes-empilhadas" },
      el(
        "div",
        { class: "estatisticas" },
        estatistica(sugestao.total_condominios, "avaliados"),
        estatistica(sugestao.total_mudancas, "trocas sugeridas"),
      ),
    ),
    el("div", { class: "acoes-empilhadas" }, botaoAplicar),
    el("h3", { class: "subtitulo" }, "Carga por fiscal após aplicar"),
    zonas(sugestao),
    el("h3", { class: "subtitulo" }, "Trocas sugeridas"),
    el(
      "div",
      { class: "tabela-rolagem rolagem-fina", tabindex: "0", role: "region", "aria-label": "Tabela de trocas sugeridas" },
      el(
        "table",
        {},
        el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "Condomínio"), el("th", { scope: "col" }, "Atual"), el("th", { scope: "col" }, "Sugerido"))),
        el("tbody", {}, sugestao.mudancas.map(linhaDaMudanca)),
      ),
    ),
    el("p", { class: "nota-tabela" }, "Clique no nome do condomínio para vê-lo no mapa."),
  );
}

async function aoCalcular() {
  const botao = document.getElementById("btn-sugerir");
  await comCarregando(botao, async () => {
    try {
      await calcularSugestao();
    } catch (erro) {
      notificar.erro("Não foi possível calcular a sugestão", humanizarErro(erro.message));
    }
  });
}

export function iniciarClustering() {
  assinar("sugestao", renderizar);
  document.getElementById("btn-sugerir").addEventListener("click", aoCalcular);
}
