import { api } from "./api.js";
import { emitir, estado, fiscalPorId, invalidarRotas } from "./estado.js";
import { distancia, nomeProprio, plural, rotuloMotivo } from "./formatacao.js";
import { notificar } from "./notificacoes.js";
import { atualizarAposMudanca, carregarFila, carregarTudo, selecionar } from "./servicos.js";

function nomeDoFiscal(id) {
  const fiscal = fiscalPorId(id);
  return fiscal ? nomeProprio(fiscal.nome) : id;
}

export function humanizarErro(mensagem) {
  return mensagem.replace(/fisc-\d+/g, (id) => nomeDoFiscal(id));
}

export async function enfileirarAusencia(payload) {
  const resposta = await api.post("/api/ausencias", payload);
  await carregarFila();
  notificar.ok(
    "Solicitação enfileirada",
    `${nomeDoFiscal(payload.fiscal_id)} · ${rotuloMotivo(payload.motivo)} · posição ${resposta.tamanho_fila} na fila`,
  );
}

function resumirDestinos(realocacoes) {
  const contagem = new Map();
  realocacoes.forEach((r) => contagem.set(r.destino_id, (contagem.get(r.destino_id) ?? 0) + 1));
  const ordenados = [...contagem.entries()].sort((a, b) => b[1] - a[1]);
  const visiveis = ordenados.slice(0, 3).map(([id, qtd]) => `${nomeDoFiscal(id)} (${qtd})`);
  const restantes = ordenados.length - visiveis.length;
  return restantes > 0 ? `${visiveis.join(", ")} e mais ${restantes}` : visiveis.join(", ");
}

export async function processarProxima() {
  let resposta;
  try {
    resposta = await api.post("/api/ausencias/processar-proxima");
  } catch (erro) {
    await carregarFila();
    throw new Error(humanizarErro(erro.message));
  }

  await atualizarAposMudanca();

  const nome = nomeDoFiscal(resposta.fiscal_id);
  console.log(
    `%cFILA (FIFO)%c Processada ausência de ${nome}: ${resposta.qtd_realocacoes} condomínio(s) redistribuído(s)`,
    "background: #b45309; color: #ffffff; font-weight: 700; padding: 2px 6px; border-radius: 4px;",
    ""
  );
  if (resposta.qtd_realocacoes === 0) {
    notificar.info(`Ausência de ${nome} registrada`, "Nenhum condomínio precisou ser redistribuído.");
    return;
  }
  notificar.ok(
    `Carteira de ${nome} redistribuída`,
    `${plural(resposta.qtd_realocacoes, "condomínio", "condomínios")} para ${resumirDestinos(resposta.realocacoes)}`,
  );
}

export async function desfazerUltima() {
  const topo = estado.historico.find((r) => r.ativa);
  const resposta = await api.post("/api/realocacoes/desfazer");
  await atualizarAposMudanca();
  const condominio = topo ? nomeProprio(topo.condominio_nome) : "Condomínio";
  console.log(
    `%cPILHA (LIFO)%c Desfeita última realocação: ${condominio} voltou para ${nomeDoFiscal(resposta.voltou_para)}`,
    "background: #be185d; color: #ffffff; font-weight: 700; padding: 2px 6px; border-radius: 4px;",
    ""
  );
  notificar.ok("Realocação desfeita", `${condominio} voltou para ${nomeDoFiscal(resposta.voltou_para)}.`);
}

export async function reverterExpiradas() {
  const resposta = await api.post("/api/realocacoes/reverter-expiradas", {});
  await atualizarAposMudanca();
  if (resposta.revertidos === 0) {
    notificar.info("Nada a reverter", "Nenhuma realocação pertence a uma ausência com período já encerrado.");
    return;
  }
  notificar.ok(
    "Realocações revertidas",
    `${plural(resposta.revertidos, "condomínio voltou", "condomínios voltaram")} ao fiscal titular.`,
  );
}

export async function calcularSugestao() {
  const { dados, ms } = await api.medido("/api/clustering/sugestao");
  console.log(
    `%cCLUSTERING (K-MEANS)%c ${dados.total_condominios} condomínios avaliados, ${dados.total_mudancas} trocas sugeridas ⏱ %c${ms.toFixed(1)} ms%c`,
    "background: #0e7490; color: #ffffff; font-weight: 700; padding: 2px 6px; border-radius: 4px;",
    "",
    "color: #10b981; font-weight: 700;",
    ""
  );
  estado.sugestao = { ...dados, ms };
  estado.aplicacaoClustering = null;
  emitir("sugestao");
}

export async function aplicarSugestao() {
  const resposta = await api.post("/api/clustering/aplicar", {
    atribuicoes: estado.sugestao._atribuicoes_completas,
  });
  estado.sugestao = null;
  estado.aplicacaoClustering = resposta.aplicadas;
  emitir("sugestao");
  await atualizarAposMudanca();
  notificar.ok(
    "Redistribuição aplicada",
    `${plural(resposta.aplicadas, "condomínio reatribuído", "condomínios reatribuídos")}.`,
  );
}

export async function reiniciarDemonstracao() {
  await api.post("/api/reset");
  invalidarRotas();
  estado.sugestao = null;
  estado.aplicacaoClustering = null;
  await carregarTudo();
  await selecionar(null);
  emitir("sugestao");
  emitir("reinicio");
  notificar.ok("Demonstração reiniciada", "Fiscais e condomínios voltaram ao estado inicial.");
}

export async function buscarEndereco(texto) {
  const { dados, ms } = await api.medido(`/api/geocodificar?q=${encodeURIComponent(texto)}`);
  return { candidatos: dados.candidatos, ms };
}

export async function cadastrarCondominio(payload) {
  const resposta = await api.post("/api/condominios", payload);
  await atualizarAposMudanca();
  notificar.ok(
    `${nomeProprio(resposta.nome)} cadastrado`,
    `Entrou na carteira de ${nomeDoFiscal(resposta.fiscal_id)}, a ${distancia(resposta.distancia_m)} do centro dela.`,
  );
  return resposta;
}
