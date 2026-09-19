import { el } from "./dom.js";
import { icone } from "./icones.js";

export function estadoVazio({ nomeIcone, titulo, texto }) {
  return el(
    "div",
    { class: "estado-vazio" },
    icone(nomeIcone),
    el("strong", {}, titulo),
    texto ? el("p", {}, texto) : null,
  );
}

export function atualizarContador(id, quantidade) {
  const no = document.getElementById(id);
  no.hidden = quantidade === 0;
  no.textContent = String(quantidade);
}

export function marcaDeFiscal(cor) {
  return el("span", { class: "fiscal-marca", "aria-hidden": "true", estilo: { "--cor": cor } });
}
