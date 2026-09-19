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
    texto.textContent = `API ${milissegundos(ms)}`;
    chip.title = "Tempo da última requisição ao servidor";
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

function iniciarControlesAuth() {
  const modalLogin = document.getElementById("modal-login");
  const btnPerfil = document.getElementById("btn-perfil");
  const btnFechar = document.getElementById("btn-fechar-login");
  const btnCancelar = document.getElementById("btn-cancelar-login");
  const btnLogout = document.getElementById("btn-logout");
  const formLogin = document.getElementById("form-login");
  const alertaErro = document.getElementById("login-erro");

  btnPerfil.addEventListener("click", () => {
    alertaErro.hidden = true;
    modalLogin.showModal();
  });

  const fechar = () => modalLogin.close();
  btnFechar.addEventListener("click", fechar);
  btnCancelar.addEventListener("click", fechar);

  document.querySelectorAll(".btn-card-perfil").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const email = btn.dataset.email;
      const senha = btn.dataset.senha;
      try {
        await fazerLogin(email, senha);
        fechar();
        await carregarDadosIniciais();
        notificar.sucesso("Acesso alterado", `Conectado como ${estado.usuario.nome}`);
      } catch (erro) {
        alertaErro.textContent = erro.message;
        alertaErro.hidden = false;
      }
    });
  });

  formLogin.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const email = document.getElementById("login-email").value.trim();
    const senha = document.getElementById("login-senha").value;
    try {
      await fazerLogin(email, senha);
      fechar();
      await carregarDadosIniciais();
      notificar.sucesso("Acesso realizado", `Conectado como ${estado.usuario.nome}`);
    } catch (erro) {
      alertaErro.textContent = erro.message;
      alertaErro.hidden = false;
    }
  });

  btnLogout.addEventListener("click", async () => {
    try {
      await fazerLogout();
      await carregarDadosIniciais();
      notificar.info("Sessão finalizada", "Você saiu da sua conta.");
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
iniciarAtalhos();

const botaoReset = document.getElementById("btn-reset");
botaoReset.addEventListener("click", () => aoReiniciar(botaoReset));

(async () => {
  try {
    await obterUsuarioAtual();
  } catch {
  }
  await carregarDadosIniciais();
})();
