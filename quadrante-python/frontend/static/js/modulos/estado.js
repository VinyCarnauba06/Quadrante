export const estado = {
  fiscais: [],
  mapaGeral: null,
  fila: [],
  historico: [],
  selecionadoId: null,
  rota: null,
  carregandoRota: false,
  sugestao: null,
  aplicacaoClustering: null,
  ordemRota: 0,
};

const ouvintes = new Map();
const cacheRotas = new Map();

export function assinar(evento, ouvinte) {
  if (!ouvintes.has(evento)) ouvintes.set(evento, new Set());
  ouvintes.get(evento).add(ouvinte);
}

export function emitir(evento) {
  ouvintes.get(evento)?.forEach((ouvinte) => ouvinte());
}

export function rotaEmCache(fiscalId) {
  return cacheRotas.get(fiscalId);
}

export function guardarRota(fiscalId, rota) {
  cacheRotas.set(fiscalId, rota);
}

export function invalidarRotas() {
  cacheRotas.clear();
}

export function fiscalPorId(id) {
  return estado.fiscais.find((f) => f.id === id) ?? null;
}

export function fiscalPorNome(nome) {
  return estado.fiscais.find((f) => f.nome === nome) ?? null;
}

export function fiscaisDeCampo() {
  return estado.fiscais.filter((f) => f.papel === "fiscal_campo");
}
