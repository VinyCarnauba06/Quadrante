import { el } from "./dom.js";
import { enderecoCurto, nomeProprio } from "./formatacao.js";

const CENTRO_MACEIO = [-9.6498, -35.7089];
const COR_CONTEXTO = "#8f8874";
const COR_INICIO = "#0a4448";
const FALHAS_PARA_TROCAR = 3;
const ZOOM_DOS_ROTULOS = 15;
const ZOOM_DE_RUA = 17;
const NS = "http://www.w3.org/2000/svg";

let mapa = null;
let camadaRota = null;
let camadaContexto = null;
let camadaDestaque = null;
let camadaPrevia = null;
let grupoBase = null;
let modo = "geral";

const pinosPorCondominio = new Map();
const dadosPorFiscal = new Map();
const pinosPorOrdem = new Map();

function desenhoDoPino({ cor, numero, largura, altura }) {
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 30 40");
  svg.setAttribute("width", String(largura));
  svg.setAttribute("height", String(altura));
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML =
    '<path d="M15 39C15 39 2 24.5 2 14.5a13 13 0 0 1 26 0C28 24.5 15 39 15 39z"/>' +
    `<circle cx="15" cy="14.5" r="${numero === undefined ? 5 : 9.5}"/>`;
  svg.style.setProperty("--cor", cor);
  return svg;
}

function iconeDoPino({ cor, numero, inicio = false, pequeno = false, previa = false }) {
  const escala = inicio ? 1.2 : pequeno ? 0.82 : 1;
  const largura = Math.round(30 * escala);
  const altura = Math.round(40 * escala);
  const no = el(
    "div",
    { class: `pin${inicio ? " inicio" : ""}${previa ? " previa" : ""}`, estilo: { "--cor": cor } },
    desenhoDoPino({ cor, numero, largura, altura }),
    numero === undefined ? null : el("span", { class: "pin-num" }, numero),
  );
  no.style.width = `${largura}px`;
  no.style.height = `${altura}px`;
  return L.divIcon({
    className: "",
    html: no,
    iconSize: [largura, altura],
    iconAnchor: [largura / 2, altura - 1],
    popupAnchor: [0, -altura + 6],
    tooltipAnchor: [largura / 2 - 2, -altura / 2],
  });
}

function conteudoPopup({ titulo, cor, detalhe, endereco }) {
  return el(
    "div",
    { class: "popup" },
    el("strong", {}, titulo),
    endereco ? el("div", { class: "popup-endereco" }, enderecoCurto(endereco)) : null,
    detalhe
      ? el(
          "div",
          { class: "popup-fiscal" },
          el("span", { class: "fiscal-marca", estilo: { "--cor": cor } }),
          detalhe,
        )
      : null,
  );
}

function criarPinoGeral({ condominio, fiscal, cor }, painel) {
  const coordenador = fiscal.papel === "coordenador";
  const nome = nomeProprio(condominio.nome);
  return L.marker([condominio.latitude, condominio.longitude], {
    icon: iconeDoPino({ cor, pequeno: coordenador }),
    pane: painel,
    title: nome,
    keyboard: false,
    riseOnHover: true,
  }).bindPopup(
    conteudoPopup({
      titulo: nome,
      cor,
      endereco: condominio.endereco,
      detalhe: `${nomeProprio(fiscal.nome)}${coordenador ? " · coordenador" : ""}`,
    }),
  );
}

function iconeDoAgrupamento(agrupamento) {
  const quantidade = agrupamento.getChildCount();
  const tamanho = quantidade < 10 ? 36 : quantidade < 30 ? 42 : 50;
  return L.divIcon({
    className: "agrupamento",
    html: `<span>${quantidade}</span>`,
    iconSize: [tamanho, tamanho],
  });
}

function criarBases(chaveGeoapify) {
  const bases = [];
  if (chaveGeoapify) {
    bases.push({
      nome: "Ruas e bairros (Geoapify)",
      camada: L.tileLayer(`https://maps.geoapify.com/v1/tile/osm-bright/{z}/{x}/{y}{r}.png?apiKey=${encodeURIComponent(chaveGeoapify)}`, {
        maxZoom: 19,
        attribution: 'Powered by <a href="https://www.geoapify.com/">Geoapify</a> &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }),
    });
    bases.push({
      nome: "Modo escuro (Geoapify)",
      camada: L.tileLayer(`https://maps.geoapify.com/v1/tile/dark-matter/{z}/{x}/{y}{r}.png?apiKey=${encodeURIComponent(chaveGeoapify)}`, {
        maxZoom: 19,
        attribution: 'Powered by <a href="https://www.geoapify.com/">Geoapify</a> &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }),
    });
    bases.push({
      nome: "Minimalista (Geoapify)",
      camada: L.tileLayer(`https://maps.geoapify.com/v1/tile/positron/{z}/{x}/{y}{r}.png?apiKey=${encodeURIComponent(chaveGeoapify)}`, {
        maxZoom: 19,
        attribution: 'Powered by <a href="https://www.geoapify.com/">Geoapify</a> &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }),
    });
  }
  bases.push({
    nome: "Satélite (Esri)",
    camada: L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
      maxZoom: 19,
      attribution: '&copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
    }),
  });
  bases.push({
    nome: "Ruas (OpenStreetMap)",
    camada: L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }),
  });
  return bases;
}

function vigiarBases(bases, aoMudarBase) {
  let falhas = 0;
  let esgotado = false;
  let manual = false;
  mapa.on("baselayerchange", () => {
    falhas = 0;
    manual = true;
  });
  bases.forEach((base, indice) => {
    base.camada.on("tileerror", () => {
      if (!mapa.hasLayer(base.camada)) return;
      falhas += 1;
      if (falhas < FALHAS_PARA_TROCAR) return;
      falhas = 0;
      if (manual) return;
      const proxima = bases[indice + 1];
      if (!proxima) {
        esgotado = true;
        aoMudarBase(false);
        return;
      }
      mapa.removeLayer(base.camada);
      proxima.camada.addTo(mapa);
    });
    base.camada.on("tileload", () => {
      falhas = 0;
      if (!esgotado) return;
      esgotado = false;
      aoMudarBase(true);
    });
  });
}

export function iniciarMapa(elemento, { aoMudarBase, chaveGeoapify = null }) {
  mapa = L.map(elemento, { center: CENTRO_MACEIO, zoom: 13, zoomControl: false, minZoom: 10, zoomSnap: 0.25 });
  L.control.zoom({ position: "bottomright", zoomInTitle: "Aproximar", zoomOutTitle: "Afastar" }).addTo(mapa);

  mapa.createPane("pinosBase").style.zIndex = "600";
  mapa.createPane("pinosDestaque").style.zIndex = "640";

  const bases = criarBases(chaveGeoapify);
  bases[0].camada.addTo(mapa);
  L.control
    .layers(Object.fromEntries(bases.map((base) => [base.nome, base.camada])), null, { position: "topright" })
    .addTo(mapa);
  const alternador = elemento.querySelector(".leaflet-control-layers-toggle");
  alternador?.setAttribute("title", "Trocar mapa base");
  alternador?.setAttribute("aria-label", "Trocar mapa base");
  vigiarBases(bases, aoMudarBase);

  camadaContexto = L.layerGroup().addTo(mapa);
  camadaRota = L.layerGroup().addTo(mapa);
  camadaDestaque = L.layerGroup().addTo(mapa);
  camadaPrevia = L.layerGroup().addTo(mapa);
  grupoBase = L.markerClusterGroup({
    maxClusterRadius: 34,
    disableClusteringAtZoom: 15,
    showCoverageOnHover: false,
    spiderfyOnMaxZoom: true,
    chunkedLoading: true,
    animate: !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    clusterPane: "pinosBase",
    iconCreateFunction: iconeDoAgrupamento,
  }).addTo(mapa);

  const atualizarRotulos = () => elemento.classList.toggle("zoom-perto", mapa.getZoom() >= ZOOM_DOS_ROTULOS);
  mapa.on("zoomend", atualizarRotulos);
  atualizarRotulos();

  new ResizeObserver(() => mapa.invalidateSize()).observe(elemento);
}

function enquadrar(pontos, { animar = true } = {}) {
  if (pontos.length === 0) return;
  if (pontos.length === 1) {
    mapa.setView(pontos[0], 16);
    return;
  }
  mapa.fitBounds(L.latLngBounds(pontos), {
    paddingTopLeft: [48, 96],
    paddingBottomRight: [48, 56],
    maxZoom: 16,
    animate: animar,
  });
}

function limparCamadas() {
  grupoBase.clearLayers();
  camadaRota.clearLayers();
  camadaContexto.clearLayers();
  camadaDestaque.clearLayers();
  mapa.getPane("pinosBase").classList.remove("esmaecido");
  pinosPorCondominio.clear();
  dadosPorFiscal.clear();
  pinosPorOrdem.clear();
}

export function desenharGeral(dados, corDe) {
  modo = "geral";
  limparCamadas();
  const todos = [];
  const pinos = [];

  dados.fiscais.forEach((fiscal) => {
    const cor = corDe(fiscal);
    const itens = fiscal.condominios.map((condominio) => ({ condominio, fiscal, cor }));
    dadosPorFiscal.set(fiscal.id, itens);
    itens.forEach((item) => {
      todos.push([item.condominio.latitude, item.condominio.longitude]);
      const pino = criarPinoGeral(item, "pinosBase");
      pinosPorCondominio.set(item.condominio.id, pino);
      pinos.push(pino);
    });
  });

  grupoBase.addLayers(pinos);
  enquadrar(todos, { animar: false });
}

export function desenharRota({ paradas, cor, geral }) {
  modo = "rota";
  limparCamadas();

  geral.fiscais.forEach((fiscal) => {
    fiscal.condominios.forEach((condominio) => {
      L.circleMarker([condominio.latitude, condominio.longitude], {
        radius: 4,
        stroke: false,
        fillColor: COR_CONTEXTO,
        fillOpacity: 0.4,
        interactive: false,
      }).addTo(camadaContexto);
    });
  });

  const caminho = paradas.map((p) => [p.latitude, p.longitude]);

  paradas.forEach((parada, indice) => {
    const inicio = indice === 0;
    const nome = nomeProprio(parada.condominio_nome);
    const pino = L.marker([parada.latitude, parada.longitude], {
      icon: iconeDoPino({ cor: inicio ? COR_INICIO : cor, numero: parada.ordem, inicio }),
      title: `${parada.ordem}. ${nome}`,
      keyboard: true,
      riseOnHover: true,
      zIndexOffset: inicio ? 500 : 0,
    })
      .bindPopup(
        conteudoPopup({
          titulo: `${parada.ordem}. ${nome}`,
          cor,
          endereco: parada.endereco,
          detalhe: inicio ? "Ponto de partida" : null,
        }),
      )
      .bindTooltip(nome, { permanent: true, direction: "right", className: "rotulo-pino", opacity: 1 })
      .addTo(camadaRota);
    pinosPorOrdem.set(parada.ordem, pino);
  });

  enquadrar(caminho);
}

export function destacarFiscal(fiscalId) {
  if (modo !== "geral") return;
  camadaDestaque.clearLayers();
  const painelBase = mapa.getPane("pinosBase");
  if (fiscalId === null) {
    painelBase.classList.remove("esmaecido");
    return;
  }
  const itens = dadosPorFiscal.get(fiscalId) ?? [];
  if (itens.length === 0) {
    painelBase.classList.remove("esmaecido");
    return;
  }
  painelBase.classList.add("esmaecido");
  itens.forEach((item) => camadaDestaque.addLayer(criarPinoGeral(item, "pinosDestaque")));
}

export function focarCondominio(condominioId) {
  const pino = pinosPorCondominio.get(condominioId);
  if (!pino) return false;
  grupoBase.zoomToShowLayer(pino, () => {
    mapa.setView(pino.getLatLng(), Math.max(mapa.getZoom(), ZOOM_DE_RUA), { animate: true });
    pino.openPopup();
  });
  return true;
}

export function focarParada(ordem) {
  const pino = pinosPorOrdem.get(ordem);
  if (!pino) return;
  mapa.setView(pino.getLatLng(), Math.max(mapa.getZoom(), ZOOM_DE_RUA), { animate: true });
  pino.openPopup();
}

export function realcarParada(ordem, ligado) {
  const pino = pinosPorOrdem.get(ordem)?.getElement()?.querySelector(".pin");
  if (pino) pino.classList.toggle("ativo", ligado);
}

export function mostrarPrevia({ latitude, longitude, cor, titulo, endereco, detalhe }) {
  camadaPrevia.clearLayers();
  const pino = L.marker([latitude, longitude], {
    icon: iconeDoPino({ cor, previa: true }),
    zIndexOffset: 1000,
    title: titulo,
    keyboard: false,
  })
    .bindPopup(conteudoPopup({ titulo, cor, detalhe, endereco }), { autoPanPaddingTopLeft: [16, 96] })
    .addTo(camadaPrevia);
  mapa.setView([latitude, longitude], Math.max(mapa.getZoom(), ZOOM_DOS_ROTULOS + 1), { animate: true });
  pino.openPopup();
}

export function limparPrevia() {
  camadaPrevia?.clearLayers();
}
