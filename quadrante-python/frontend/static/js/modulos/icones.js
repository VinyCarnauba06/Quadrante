const CAMINHOS = {
  check: '<path d="M20 6 9 17l-5-5"/>',
  alerta: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  fechar: '<path d="M18 6 6 18M6 6l12 12"/>',
  reiniciar: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
  mapa: '<path d="M9 4 3 6.5v13L9 17l6 3 6-2.5v-13L15 7z"/><path d="M9 4v13M15 7v13"/>',
  mais: '<path d="M12 5v14M5 12h14"/>',
  proximo: '<path d="m6 4 10 8-10 8z"/><path d="M19 5v14"/>',
  desfazer: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
  relogio: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  grupo: '<circle cx="12" cy="12" r="2"/><circle cx="5" cy="6" r="2"/><circle cx="19" cy="7" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="18" r="2"/><path d="M6.6 7.2 10.4 11M13.8 11l3.8-3M10.5 13.2 7.3 17.3M13.6 13.4l3 3.3"/>',
  seta: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  rota: '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
  fila: '<path d="M4 6h16M4 12h16M4 18h10"/>',
  pilha: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
  usuarios: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
};

const NS = "http://www.w3.org/2000/svg";

export function icone(nome) {
  const envoltorio = document.createElement("span");
  envoltorio.className = "icone";
  envoltorio.setAttribute("aria-hidden", "true");
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.innerHTML = CAMINHOS[nome] ?? "";
  envoltorio.append(svg);
  return envoltorio;
}

export function hidratarIcones(raiz = document) {
  raiz.querySelectorAll("[data-icone]").forEach((no) => {
    const nome = no.dataset.icone;
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.innerHTML = CAMINHOS[nome] ?? "";
    no.replaceChildren(svg);
    no.removeAttribute("data-icone");
  });
}
