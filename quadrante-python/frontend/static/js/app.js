import { aoMedir } from "./modulos/api.js";
import { reiniciarDemonstracao } from "./modulos/acoes.js";
import { fazerLogin, fazerLogout, obterUsuarioAtual } from "./modulos/auth.js";
import { confirmar } from "./modulos/dialogo.js";
import { comCarregando } from "./modulos/dom.js";
import { assinar, estado } from "./modulos/estado.js";
import { milissegundos } from "./modulos/formatacao.js";
import { hidratarIcones } from "./modulos/icones.js";
import { iniciarControladorMapa } from "./modulos/controlador-mapa.js";
import { notificar } from "./modulos/notificacoes.js";
import { iniciarAusencias } from "./modulos/painel-ausencias.js";
import { iniciarCadastro } from "./modulos/painel-cadastro.js";
import { iniciarClustering } from "./modulos/painel-clustering.js";
import { iniciarEquipe, mostrarEsqueleto, mostrarFalhaDeCarga } from "./modulos/painel-equipe.js";
import { iniciarHistorico } from "./modulos/painel-historico.js";
import { iniciarRota } from "./modulos/painel-rota.js";
import { carregarTudo, selecionar } from "./modulos/servicos.js";
import { abrirAba, iniciarTabs } from "./modulos/tabs.js";
import { iniciarPainelEstruturas } from "./modulos/painel-estruturas.js";

const LIMITE_LENTO_MS = 250;

function iniciarStatusDaApi() {
  const chip = document.getElementById("status-api");
  const texto = document.getElementById("status-api-texto");
  aoMedir(({ ok, ms }) => {
    if (!ok) {
      chip.dataset.estado = "erro";
      texto.textContent = "sem resposta";
      return;
    }
    chip.dataset.estado = ms > LIMITE_LENTO_MS ? "lento" : "ok";
    texto.textContent = "online";
    chip.title = `Conectado ao servidor (${milissegundos(ms)})`;
  });
}

function aplicarPermissoesPerfil(usuario) {
  const tabAusencias = document.getElementById("tab-ausencias");
  const tabHistorico = document.getElementById("tab-historico");
  const tabKmeans = document.getElementById("tab-kmeans");
  const tabCadastro = document.getElementById("tab-cadastro");
  const btnReset = document.getElementById("btn-reset");

  const papel = usuario ? usuario.papel : "admin";

  if (papel === "fiscal_campo") {
    tabAusencias.hidden = true;
    tabHistorico.hidden = true;
    tabKmeans.hidden = true;
    tabCadastro.hidden = true;
    btnReset.hidden = true;
    abrirAba("rota");
    if (usuario && usuario.id) {
      selecionar(usuario.id);
    }
  } else if (papel === "operador") {
    tabAusencias.hidden = false;
    tabHistorico.hidden = false;
    tabKmeans.hidden = true;
    tabCadastro.hidden = false;
    btnReset.hidden = true;
  } else {
    tabAusencias.hidden = false;
    tabHistorico.hidden = false;
    tabKmeans.hidden = false;
    tabCadastro.hidden = false;
    btnReset.hidden = false;
  }
}

function atualizarCabecalhoUsuario() {
  const usuario = estado.usuario;
  const nomeEl = document.getElementById("usuario-nome");
  const badgeEl = document.getElementById("usuario-badge");
  const btnLogout = document.getElementById("btn-logout");

  if (!usuario) {
    nomeEl.textContent = "Entrar";
    badgeEl.hidden = true;
    btnLogout.hidden = true;
    return;
  }

  nomeEl.textContent = usuario.nome.split(" ")[0];
  badgeEl.hidden = false;
  badgeEl.className = "badge-papel";

  if (usuario.papel === "admin") {
    badgeEl.textContent = "Admin";
    badgeEl.classList.add("badge-papel-admin");
  } else if (usuario.papel === "operador") {
    badgeEl.textContent = "Operador";
    badgeEl.classList.add("badge-papel-operador");
  } else {
    badgeEl.textContent = "Fiscal";
    badgeEl.classList.add("badge-papel-fiscal");
  }

  btnLogout.hidden = false;
}

function alternarTela(autenticado) {
  const telaLogin = document.getElementById("tela-login");
  const appEl = document.getElementById("app");
  if (autenticado) {
    if (telaLogin) telaLogin.hidden = true;
    if (appEl) appEl.hidden = false;
  } else {
    if (telaLogin) telaLogin.hidden = false;
    if (appEl) appEl.hidden = true;
  }
}

function iniciarControlesAuth() {
  const modalLogin = document.getElementById("modal-login");
  const btnPerfil = document.getElementById("btn-perfil");
  const btnFechar = document.getElementById("btn-fechar-login");
  const btnCancelar = document.getElementById("btn-cancelar-login");
  const btnLogout = document.getElementById("btn-logout");
  const formModalLogin = document.getElementById("form-login");
  const alertaModalErro = document.getElementById("login-erro");

  const formTelaLogin = document.getElementById("form-tela-login");
  const alertaTelaErro = document.getElementById("tela-login-erro");

  btnPerfil.addEventListener("click", () => {
    alertaModalErro.hidden = true;
    modalLogin.showModal();
  });

  const fecharModal = () => modalLogin.close();
  btnFechar.addEventListener("click", fecharModal);
  btnCancelar.addEventListener("click", fecharModal);

  async function efetuarLogin(email, senha, erroEl) {
    if (erroEl) erroEl.hidden = true;
    try {
      await fazerLogin(email, senha);
      if (modalLogin.open) fecharModal();
      alternarTela(true);
      await carregarDadosIniciais();
      notificar.ok("Acesso realizado", `Conectado como ${estado.usuario.nome}`);
    } catch (erro) {
      if (erroEl) {
        erroEl.textContent = erro.message;
        erroEl.hidden = false;
      } else {
        notificar.erro("Erro de autenticação", erro.message);
      }
    }
  }

  document.querySelectorAll(".btn-card-perfil").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const email = btn.dataset.email;
      const senha = btn.dataset.senha;
      const erroEl = btn.closest("#tela-login") ? alertaTelaErro : alertaModalErro;
      await efetuarLogin(email, senha, erroEl);
    });
  });

  if (formTelaLogin) {
    formTelaLogin.addEventListener("submit", async (evento) => {
      evento.preventDefault();
      const email = document.getElementById("tela-login-email").value.trim();
      const senha = document.getElementById("tela-login-senha").value;
      await efetuarLogin(email, senha, alertaTelaErro);
    });
  }

  formModalLogin.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const email = document.getElementById("login-email").value.trim();
    const senha = document.getElementById("login-senha").value;
    await efetuarLogin(email, senha, alertaModalErro);
  });

  btnLogout.addEventListener("click", async () => {
    try {
      await fazerLogout();
      alternarTela(false);
      notificar.ok("Sessão finalizada", "Você saiu da sua conta.");
    } catch (erro) {
      notificar.erro("Erro ao sair", erro.message);
    }
  });

  assinar("usuario", () => {
    atualizarCabecalhoUsuario();
    aplicarPermissoesPerfil(estado.usuario);
  });
}

async function aoReiniciar(botao) {
  const confirmado = await confirmar({
    titulo: "Reiniciar a demonstração?",
    texto: "Fila de ausências, histórico de realocações e sugestões voltam ao estado inicial, e os condomínios retornam aos fiscais originais. Isso não pode ser desfeito.",
    rotuloConfirmar: "Reiniciar",
    perigo: true,
  });
  if (!confirmado) return;
  await comCarregando(botao, async () => {
    try {
      await reiniciarDemonstracao();
    } catch (erro) {
      notificar.erro("Não foi possível reiniciar", erro.message);
    }
  });
}

async function carregarDadosIniciais() {
  mostrarEsqueleto();
  try {
    await carregarTudo();
  } catch (erro) {
    notificar.erro("Não foi possível carregar os dados", erro.message);
    mostrarFalhaDeCarga(carregarDadosIniciais);
  }
}

function iniciarAtalhos() {
  document.addEventListener("keydown", (evento) => {
    if (evento.key !== "Escape" || document.getElementById("dialogo").open || document.getElementById("modal-login").open) return;
    if (estado.selecionadoId !== null && estado.usuario?.papel !== "fiscal_campo") selecionar(null);
  });
}

hidratarIcones();
iniciarTabs();
iniciarStatusDaApi();
iniciarControlesAuth();
iniciarControladorMapa();
iniciarEquipe();
iniciarRota();
iniciarAusencias();
iniciarHistorico();
iniciarClustering();
iniciarCadastro();
iniciarPainelEstruturas();
iniciarAtalhos();

const botaoReset = document.getElementById("btn-reset");
botaoReset.addEventListener("click", () => aoReiniciar(botaoReset));

(async () => {
  let usuario = null;
  try {
    usuario = await obterUsuarioAtual();
  } catch {
    usuario = null;
  }
  if (!usuario) {
    alternarTela(false);
  } else {
    alternarTela(true);
    await carregarDadosIniciais();
  }
})();

const bannerTitulo = "background: #0284c7; color: #ffffff; font-size: 12px; font-weight: bold; padding: 4px 8px; border-radius: 4px;";
const bannerCorpo = "color: #94a3b8; font-size: 11px;";
console.log("%cQUADRANTE — Monitoramento e Log de Performance Ativo%c", bannerTitulo, "");
console.log(
  "%cEstruturas de Dados: Vetor, Lista Encadeada, Fila (FIFO), Pilha (LIFO)\nLatências de rede, cálculo de rotas e redistribuição são monitoradas em tempo real.\nExecute %cquadrante.benchmark()%c no console para rodar um teste completo de latência.",
  bannerCorpo,
  "color: #38bdf8; font-weight: bold;",
  bannerCorpo
);

window.quadrante = {
  async benchmark() {
    console.log("%c[BENCHMARK] Executando medição de latência das operações...", "color: #38bdf8; font-weight: bold;");
    const operacoes = [
      { nome: "GET /api/fiscais (Vetor)", url: "/api/fiscais" },
      { nome: "GET /api/mapa-geral (Vetor)", url: "/api/mapa-geral" },
      { nome: "GET /api/ausencias/fila (Fila FIFO)", url: "/api/ausencias/fila" },
      { nome: "GET /api/historico (Pilha LIFO)", url: "/api/historico" },
      { nome: "GET /api/clustering/sugestao (K-Means)", url: "/api/clustering/sugestao" },
    ];
    const resultados = [];
    for (const op of operacoes) {
      const t0 = performance.now();
      try {
        const resp = await fetch(op.url);
        const t1 = performance.now();
        resultados.push({
          Operacao: op.nome,
          Status: resp.status,
          "Latencia (ms)": parseFloat((t1 - t0).toFixed(2)),
          Resultado: resp.ok ? "OK" : "FALHA",
        });
      } catch (err) {
        resultados.push({
          Operacao: op.nome,
          Status: "Erro",
          "Latencia (ms)": 0,
          Resultado: err.message,
        });
      }
    }
    console.table(resultados);
    const media = resultados.reduce((acc, r) => acc + r["Latencia (ms)"], 0) / resultados.length;
    console.log(`%c[BENCHMARK] Média geral de latência: ${media.toFixed(2)} ms`, "color: #10b981; font-weight: bold;");
    return resultados;
  },
};
