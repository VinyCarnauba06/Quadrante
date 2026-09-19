import { buscarEndereco, cadastrarCondominio, humanizarErro } from "./acoes.js";
import { estadoVazio, marcaDeFiscal } from "./componentes.js";
import { corDoFiscal } from "./cores.js";
import { comCarregando, desabilitar, el, estaDesabilitado } from "./dom.js";
import { assinar, estado, fiscalPorId } from "./estado.js";
import { distancia, enderecoCurto, milissegundos, nomeProprio, plural } from "./formatacao.js";
import { focarCondominio, limparPrevia, mostrarPrevia } from "./mapa.js";
import { notificar } from "./notificacoes.js";
import { selecionar } from "./servicos.js";

const campo = (id) => document.getElementById(id);
const layoutEmpilhado = window.matchMedia("(max-width: 980px)");

let candidatos = [];
let escolhido = null;
let ultimoMs = null;

function geocodificacaoAtiva() {
  return campo("painel-cadastro").dataset.geocodificacao === "ativa";
}

function mostrarErro(idCampo, idErro, mensagem) {
  const erro = campo(idErro);
  erro.textContent = mensagem;
  erro.hidden = mensagem === "";
  campo(idCampo).setAttribute("aria-invalid", String(mensagem !== ""));
}

function precisao(confianca) {
  if (confianca === null || confianca === undefined) return null;
  if (confianca >= 0.9) return "precisão alta";
  if (confianca >= 0.6) return "precisão média";
  return "precisão baixa";
}

function corDoCandidato(candidato) {
  return corDoFiscal(fiscalPorId(candidato.fiscal_sugerido_id));
}

function atualizarBotaoCadastrar() {
  const pronto = escolhido !== null && campo("cadastro-nome").value.trim() !== "";
  desabilitar(
    campo("btn-cadastrar"),
    !pronto,
    escolhido === null ? "Busque e escolha um endereço" : "Informe o nome do condomínio",
  );
}

function mostrarPreviaDoEscolhido() {
  if (escolhido === null) return;
  const nome = campo("cadastro-nome").value.trim();
  mostrarPrevia({
    latitude: escolhido.latitude,
    longitude: escolhido.longitude,
    cor: corDoCandidato(escolhido),
    titulo: nome === "" ? "Novo condomínio" : nomeProprio(nome),
    endereco: escolhido.endereco,
    detalhe: escolhido.fiscal_sugerido_nome ? `Iria para ${nomeProprio(escolhido.fiscal_sugerido_nome)}` : "Sem fiscal disponível",
  });
}

async function aoEscolher(candidato) {
  escolhido = candidato;
  if (estado.selecionadoId !== null) await selecionar(null);
  renderizarCandidatos();
  atualizarBotaoCadastrar();
  mostrarPreviaDoEscolhido();
}

function cartaoDoCandidato(candidato) {
  const selecionado = candidato === escolhido;
  const nivel = precisao(candidato.confianca);
  return el(
    "button",
    {
      type: "button",
      class: `candidato${selecionado ? " selecionado" : ""}`,
      "aria-pressed": String(selecionado),
      onclick: () => aoEscolher(candidato),
    },
    el("span", { class: "candidato-endereco" }, enderecoCurto(candidato.endereco)),
    el(
      "span",
      { class: "candidato-meta" },
      candidato.bairro ? el("span", { class: "tag" }, candidato.bairro) : null,
      nivel ? el("span", { class: "candidato-precisao" }, nivel) : null,
    ),
    candidato.fiscal_sugerido_nome
      ? el(
          "span",
          { class: "candidato-destino" },
          marcaDeFiscal(corDoCandidato(candidato)),
          `${nomeProprio(candidato.fiscal_sugerido_nome)} · ${distancia(candidato.distancia_m)} do centro da carteira`,
        )
      : el("span", { class: "candidato-destino" }, "Nenhum fiscal de campo disponível"),
  );
}

function renderizarCandidatos() {
  const alvo = campo("cadastro-resultado");
  if (candidatos.length === 0) {
    alvo.replaceChildren();
    return;
  }
  alvo.replaceChildren(
    el(
      "h3",
      { class: "subtitulo" },
      `${plural(candidatos.length, "resultado", "resultados")}`,
      ultimoMs === null ? null : el("span", { class: "subtitulo-ms" }, ` · Geoapify ${milissegundos(ultimoMs)}`),
    ),
    el("div", { class: "candidatos", role: "group", "aria-label": "Endereços encontrados" }, candidatos.map(cartaoDoCandidato)),
  );
}

function renderizarSemResultado() {
  campo("cadastro-resultado").replaceChildren(
    estadoVazio({
      nomeIcone: "mapa",
      titulo: "Nenhum endereço encontrado",
      texto: "Confira a grafia ou inclua o bairro. A busca cobre Maceió e região.",
    }),
  );
}

function limparBusca() {
  candidatos = [];
  escolhido = null;
  limparPrevia();
  campo("cadastro-resultado").replaceChildren();
  atualizarBotaoCadastrar();
}

async function aoBuscar(evento) {
  evento.preventDefault();
  const texto = campo("cadastro-endereco").value.trim();
  if (texto.length < 3) {
    mostrarErro("cadastro-endereco", "erro-cadastro-endereco", "Digite ao menos 3 caracteres do endereço.");
    campo("cadastro-endereco").focus();
    return;
  }
  mostrarErro("cadastro-endereco", "erro-cadastro-endereco", "");
  limparBusca();
  await comCarregando(campo("btn-buscar-endereco"), async () => {
    try {
      const { candidatos: encontrados, ms } = await buscarEndereco(texto);
      candidatos = encontrados;
      ultimoMs = ms;
      if (candidatos.length === 0) {
        renderizarSemResultado();
        return;
      }
      renderizarCandidatos();
      if (candidatos.length === 1) await aoEscolher(candidatos[0]);
    } catch (erro) {
      notificar.erro("Não foi possível buscar o endereço", erro.message);
    }
  });
}

async function aoCadastrar() {
  const botao = campo("btn-cadastrar");
  if (estaDesabilitado(botao)) {
    if (campo("cadastro-nome").value.trim() === "") {
      mostrarErro("cadastro-nome", "erro-cadastro-nome", "Informe o nome do condomínio.");
      campo("cadastro-nome").focus();
    }
    return;
  }
  const alvo = escolhido;
  await comCarregando(botao, async () => {
    try {
      const resposta = await cadastrarCondominio({
        nome: campo("cadastro-nome").value.trim(),
        endereco: alvo.endereco,
        latitude: alvo.latitude,
        longitude: alvo.longitude,
      });
      reiniciarFormulario();
      if (estado.selecionadoId !== null) await selecionar(null);
      focarCondominio(resposta.id);
      if (layoutEmpilhado.matches) document.getElementById("palco").scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (erro) {
      notificar.erro("Não foi possível cadastrar", humanizarErro(erro.message));
    }
  });
}

function reiniciarFormulario() {
  campo("cadastro-nome").value = "";
  campo("cadastro-endereco").value = "";
  mostrarErro("cadastro-nome", "erro-cadastro-nome", "");
  mostrarErro("cadastro-endereco", "erro-cadastro-endereco", "");
  limparBusca();
}

function ligarPreviaAoFocoDaAba() {
  document.querySelectorAll('[role="tab"]').forEach((aba) => {
    aba.addEventListener("click", () => {
      if (aba.id === "tab-cadastro") mostrarPreviaDoEscolhido();
      else limparPrevia();
    });
  });
}

export function iniciarCadastro() {
  if (!geocodificacaoAtiva()) {
    campo("cadastro-aviso").hidden = false;
    desabilitar(campo("btn-buscar-endereco"), true, "Configure GEOAPIFY_API_KEY");
  }
  atualizarBotaoCadastrar();
  ligarPreviaAoFocoDaAba();
  assinar("reinicio", reiniciarFormulario);
  campo("form-cadastro").addEventListener("submit", (evento) => {
    if (!geocodificacaoAtiva()) {
      evento.preventDefault();
      return;
    }
    aoBuscar(evento);
  });
  campo("cadastro-nome").addEventListener("input", () => {
    mostrarErro("cadastro-nome", "erro-cadastro-nome", "");
    atualizarBotaoCadastrar();
  });
  campo("cadastro-endereco").addEventListener("input", () => mostrarErro("cadastro-endereco", "erro-cadastro-endereco", ""));
  campo("btn-cadastrar").addEventListener("click", aoCadastrar);
}
