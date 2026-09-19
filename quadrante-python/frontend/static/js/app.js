import { aoMedir } from "./modulos/api.js";
import { reiniciarDemonstracao } from "./modulos/acoes.js";
import { confirmar } from "./modulos/dialogo.js";
import { comCarregando } from "./modulos/dom.js";
import { estado } from "./modulos/estado.js";
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
import { iniciarTabs } from "./modulos/tabs.js";

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
    if (evento.key !== "Escape" || document.getElementById("dialogo").open) return;
    if (estado.selecionadoId !== null) selecionar(null);
  });
}

hidratarIcones();
iniciarTabs();
iniciarStatusDaApi();
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

carregarDadosIniciais();
