import { api } from "./api.js";
import { emitir, estado, fiscalPorId, guardarRota, invalidarRotas, rotaEmCache } from "./estado.js";
import { notificar } from "./notificacoes.js";

export async function carregarFiscais() {
  estado.fiscais = await api.get("/api/fiscais");
  emitir("fiscais");
}

export async function carregarMapaGeral() {
  estado.mapaGeral = await api.get("/api/mapa-geral");
  emitir("mapa");
}

export async function carregarFila() {
  estado.fila = await api.get("/api/ausencias/fila");
  emitir("fila");
}

export async function carregarHistorico() {
  estado.historico = await api.get("/api/historico");
  emitir("historico");
}

export async function carregarTudo() {
  await carregarFiscais();
  await Promise.all([carregarMapaGeral(), carregarFila(), carregarHistorico()]);
}

export async function selecionar(id) {
  estado.selecionadoId = id;
  const ordem = ++estado.ordemRota;
  const fiscal = fiscalPorId(id);

  if (!fiscal || fiscal.papel !== "fiscal_campo") {
    estado.rota = null;
    estado.carregandoRota = false;
    emitir("selecao");
    emitir("rota");
    return;
  }

  const emCache = rotaEmCache(id);
  if (emCache) {
    estado.rota = { ...emCache, ms: 0, doCache: true };
    estado.carregandoRota = false;
    emitir("selecao");
    emitir("rota");
    return;
  }

  estado.rota = null;
  estado.carregandoRota = true;
  emitir("selecao");
  emitir("rota");

  try {
    const { dados, ms } = await api.medido(`/api/fiscais/${id}/rota`);
    if (ordem !== estado.ordemRota) return;
    guardarRota(id, dados);
    estado.rota = { ...dados, ms, doCache: false };
  } catch (erro) {
    if (ordem !== estado.ordemRota) return;
    estado.selecionadoId = null;
    estado.rota = null;
    notificar.erro("Não foi possível calcular a rota", erro.message);
    emitir("selecao");
  } finally {
    if (ordem === estado.ordemRota) {
      estado.carregandoRota = false;
      emitir("rota");
    }
  }
}

export async function atualizarAposMudanca() {
  invalidarRotas();
  if (estado.sugestao) {
    estado.sugestao = null;
    emitir("sugestao");
  }
  await Promise.all([carregarFiscais(), carregarMapaGeral(), carregarFila(), carregarHistorico()]);
  if (estado.selecionadoId) await selecionar(estado.selecionadoId);
}
