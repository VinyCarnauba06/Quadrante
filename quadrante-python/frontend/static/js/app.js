const estado = { fiscalSelecionado: null, ultimaSugestao: null };

const CENTRO_MACEIO = [-9.6498, -35.7089];
const PALETA_FISCAIS = [
  "#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed",
  "#0891b2", "#db2777", "#65a30d", "#ea580c", "#4338ca",
];

const mapa = L.map("mapa", { center: CENTRO_MACEIO, zoom: 13 });
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 19,
}).addTo(mapa);
const camadaMapa = L.layerGroup().addTo(mapa);

function corParaFiscal(fiscalId, ordemFiscais) {
  const indice = ordemFiscais.indexOf(fiscalId);
  return PALETA_FISCAIS[Math.max(indice, 0) % PALETA_FISCAIS.length];
}

function enquadrar(pontos) {
  if (pontos.length === 0) return;
  if (pontos.length === 1) {
    mapa.setView(pontos[0], 15);
    return;
  }
  mapa.fitBounds(L.latLngBounds(pontos), { padding: [40, 40], maxZoom: 16 });
}

async function renderizarMapaGeral() {
  const dados = await api("/api/mapa-geral");
  camadaMapa.clearLayers();
  const ordemFiscaisCampo = dados.fiscais.filter((f) => f.papel === "fiscal_campo").map((f) => f.id);
  const todosPontos = [];

  dados.fiscais.forEach((f) => {
    const cor = f.papel === "coordenador" ? "#94a3b8" : corParaFiscal(f.id, ordemFiscaisCampo);
    f.condominios.forEach((c) => {
      const ponto = [c.latitude, c.longitude];
      todosPontos.push(ponto);
      L.circleMarker(ponto, {
        radius: f.papel === "coordenador" ? 5 : 7,
        color: "white",
        weight: 1.5,
        fillColor: cor,
        fillOpacity: 0.9,
      })
        .bindPopup(`<strong>${c.nome}</strong><br>${f.nome}${f.papel === "coordenador" ? " (coordenador)" : ""}`)
        .addTo(camadaMapa);
    });
  });

  enquadrar(todosPontos);
}

function renderizarMapaRota(paradas) {
  camadaMapa.clearLayers();
  if (paradas.length === 0) return;

  const caminho = paradas.map((p) => [p.latitude, p.longitude]);
  L.polyline(caminho, { color: "#2563eb", weight: 3, opacity: 0.85 }).addTo(camadaMapa);

  paradas.forEach((p, i) => {
    const icone = L.divIcon({
      className: "",
      html: `<div class="marcador-numero${i === 0 ? " inicio" : ""}">${p.ordem}</div>`,
      iconSize: [22, 22],
      iconAnchor: [11, 11],
    });
    L.marker([p.latitude, p.longitude], { icon: icone })
      .bindPopup(`<strong>${p.ordem}. ${p.condominio_nome}</strong>`)
      .addTo(camadaMapa);
  });

  enquadrar(caminho);
}

async function api(caminho, opcoes = {}) {
  const resp = await fetch(caminho, {
    headers: { "Content-Type": "application/json" },
    ...opcoes,
  });
  const dados = await resp.json();
  if (!resp.ok) throw new Error(dados.erro || "erro desconhecido");
  return dados;
}

function mensagem(elId, texto, tipo) {
  const el = document.getElementById(elId);
  el.innerHTML = `<div class="status-msg ${tipo}">${texto}</div>`;
  setTimeout(() => { el.innerHTML = ""; }, 5000);
}

async function carregarFiscais() {
  const fiscais = await api("/api/fiscais");
  const container = document.getElementById("lista-fiscais");
  const select = document.getElementById("ausencia-fiscal");

  container.innerHTML = "";
  select.innerHTML = "";

  fiscais.forEach((f) => {
    const item = document.createElement("div");
    item.className = "fiscal-item" + (f.papel === "coordenador" ? " coordenador" : "");
    item.dataset.id = f.id;
    item.innerHTML = `<span>${f.nome}</span><span class="badge">${f.qtd_condominios} condomínios</span>`;
    item.addEventListener("click", () => selecionarFiscal(f));
    container.appendChild(item);

    if (f.papel === "fiscal_campo") {
      const opt = document.createElement("option");
      opt.value = f.id;
      opt.textContent = f.nome;
      select.appendChild(opt);
    }
  });
}

async function selecionarFiscal(fiscal) {
  document.querySelectorAll(".fiscal-item").forEach((el) => el.classList.remove("selecionado"));
  document.querySelector(`.fiscal-item[data-id="${fiscal.id}"]`)?.classList.add("selecionado");
  estado.fiscalSelecionado = fiscal;

  if (fiscal.papel === "coordenador") {
    document.getElementById("titulo-mapa").textContent = "Mapa geral — carteira por fiscal";
    await renderizarMapaGeral();
    document.getElementById("info-rota").innerHTML = `<p class="vazio">${fiscal.nome} é coordenador — carteira fixa, não entra em rota/realocação.</p>`;
    return;
  }

  document.getElementById("titulo-mapa").textContent = `Rota otimizada — ${fiscal.nome}`;
  document.getElementById("info-rota").innerHTML = `<p class="vazio">calculando rota (TSP)…</p>`;

  const rota = await api(`/api/fiscais/${fiscal.id}/rota`);
  renderizarMapaRota(rota.paradas.filter((p) => p.latitude != null && p.longitude != null));
  document.getElementById("info-rota").innerHTML =
    `<p><strong>${rota.distancia_total_km} km</strong> · ${rota.paradas.length} paradas — ordem otimizada por nearest-neighbor + 2-opt.</p>`;

  await carregarFiscais();
}

async function carregarFila() {
  const fila = await api("/api/ausencias/fila"); // já vem frente -> fim
  const container = document.getElementById("fila-ausencias");
  if (fila.length === 0) {
    container.innerHTML = `<p class="vazio">fila vazia — nenhuma solicitação de ausência aguardando</p>`;
    return;
  }
  container.innerHTML = `
    <div class="fila-trilha">
      ${fila.map((s, i) => `
        <div class="caixa-estrutura ${i === 0 ? "destaque" : ""}">
          ${i === 0 ? '<span class="rotulo-destaque">próxima a atender</span>' : ""}
          <strong>${s.fiscal_nome}</strong>
          <span>${s.motivo}</span>
          <span class="periodo">${s.data_inicio.slice(0,10)} a ${s.data_fim.slice(0,10)}</span>
        </div>
        ${i < fila.length - 1 ? '<span class="seta-fila">→</span>' : ""}
      `).join("")}
    </div>`;
}

async function carregarHistorico() {
  const historico = await api("/api/historico"); // já vem topo -> base
  const container = document.getElementById("historico");
  if (historico.length === 0) {
    container.innerHTML = `<p class="vazio">nenhuma realocação ainda</p>`;
    return;
  }
  container.innerHTML = historico.slice(0, 10).map((r, i) => `
    <div class="caixa-estrutura pilha ${i === 0 && r.ativa ? "destaque" : ""} ${r.ativa ? "" : "revertida"}">
      ${i === 0 && r.ativa ? '<span class="rotulo-destaque">topo — próxima a desfazer</span>' : ""}
      <strong>${r.condominio_nome}</strong>
      <span>${r.de_nome} → ${r.para_nome}</span>
      <span class="tag ${r.ativa ? "ativa" : "revertida"}">${r.ativa ? "ativa" : "revertida"}</span>
    </div>
  `).join("");
}

document.getElementById("form-ausencia").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const payload = {
    fiscal_id: document.getElementById("ausencia-fiscal").value,
    motivo: document.getElementById("ausencia-motivo").value,
    data_inicio: document.getElementById("ausencia-inicio").value,
    data_fim: document.getElementById("ausencia-fim").value,
  };
  try {
    const res = await api("/api/ausencias", { method: "POST", body: JSON.stringify(payload) });
    mensagem("msg-ausencia", `Enfileirada. Fila agora com ${res.tamanho_fila} solicitação(ões).`, "ok");
    await carregarFila();
  } catch (e) {
    mensagem("msg-ausencia", e.message, "erro");
  }
});

document.getElementById("btn-processar-fila").addEventListener("click", async () => {
  try {
    const res = await api("/api/ausencias/processar-proxima", { method: "POST" });
    mensagem("msg-ausencia", `${res.fiscal_id}: ${res.qtd_realocacoes} condomínio(s) redistribuído(s).`, "ok");
    await Promise.all([carregarFila(), carregarHistorico(), carregarFiscais()]);
  } catch (e) {
    mensagem("msg-ausencia", e.message, "erro");
  }
});

document.getElementById("btn-reverter-expiradas").addEventListener("click", async () => {
  try {
    const res = await api("/api/realocacoes/reverter-expiradas", { method: "POST", body: JSON.stringify({}) });
    mensagem("msg-ausencia", `${res.revertidos} realocação(ões) revertida(s).`, "ok");
    await Promise.all([carregarHistorico(), carregarFiscais()]);
  } catch (e) {
    mensagem("msg-ausencia", e.message, "erro");
  }
});

document.getElementById("btn-desfazer").addEventListener("click", async () => {
  try {
    const res = await api("/api/realocacoes/desfazer", { method: "POST" });
    mensagem("msg-ausencia", `Desfeito: ${res.condominio_id} voltou para ${res.voltou_para}.`, "ok");
    await Promise.all([carregarHistorico(), carregarFiscais()]);
  } catch (e) {
    mensagem("msg-ausencia", e.message, "erro");
  }
});

document.getElementById("btn-sugerir").addEventListener("click", async () => {
  const container = document.getElementById("resultado-clustering");
  container.innerHTML = `<p class="vazio">rodando k-means…</p>`;
  try {
    const sug = estado.ultimaSugestao = await api("/api/clustering/sugestao");
    const zonas = Object.entries(sug.tamanho_por_zona).map(([nome, qtd]) => `${nome}: ${qtd}`).join(" · ");
    container.innerHTML = `
      <p>${sug.total_condominios} condomínios avaliados, <strong>${sug.total_mudancas} mudanças</strong> sugeridas.</p>
      <p class="vazio">${zonas}</p>
      <table>
        <thead><tr><th>Condomínio</th><th>Atual</th><th>Sugerido</th></tr></thead>
        <tbody>
          ${sug.mudancas.slice(0, 10).map((m) => `
            <tr>
              <td>${m.condominio_nome}</td>
              <td>${m.fiscal_atual_nome}</td>
              <td><span class="tag mudou">${m.fiscal_sugerido_nome}</span></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
      <div class="acoes"><button id="btn-aplicar-clustering" class="primario">Aplicar todas as mudanças sugeridas</button></div>
    `;
    document.getElementById("btn-aplicar-clustering").addEventListener("click", aplicarClustering);
  } catch (e) {
    container.innerHTML = `<div class="status-msg erro">${e.message}</div>`;
  }
});

async function aplicarClustering() {
  if (!estado.ultimaSugestao) return;
  try {
    const res = await api("/api/clustering/aplicar", {
      method: "POST",
      body: JSON.stringify({ atribuicoes: estado.ultimaSugestao._atribuicoes_completas }),
    });
    mensagem("msg-ausencia", `${res.aplicadas} condomínio(s) reatribuído(s).`, "ok");
    await renderizarMapaGeral();
    await carregarFiscais();
  } catch (e) {
    mensagem("msg-ausencia", e.message, "erro");
  }
}

document.getElementById("btn-reset").addEventListener("click", async () => {
  try {
    await api("/api/reset", { method: "POST" });
    document.getElementById("titulo-mapa").textContent = "Mapa geral — carteira por fiscal";
    document.getElementById("info-rota").innerHTML = "";
    document.getElementById("resultado-clustering").innerHTML = "";
    estado.ultimaSugestao = null;
    estado.fiscalSelecionado = null;
    await Promise.all([carregarFiscais(), carregarFila(), carregarHistorico(), renderizarMapaGeral()]);
    mensagem("msg-ausencia", "Demonstração reiniciada — estado real da Prolar AGE recarregado.", "ok");
  } catch (e) {
    mensagem("msg-ausencia", e.message, "erro");
  }
});

(async function iniciar() {
  await carregarFiscais();
  await carregarFila();
  await carregarHistorico();
  await renderizarMapaGeral();
})();
