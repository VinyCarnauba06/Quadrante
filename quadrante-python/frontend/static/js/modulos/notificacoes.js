import { el } from "./dom.js";
import { icone } from "./icones.js";

const LIMITE = 4;
const DURACAO = { ok: 5000, info: 5000, erro: 9000 };
const ICONE = { ok: "check", info: "info", erro: "alerta" };

function areaDeToasts() {
  return document.getElementById("toasts");
}

function mostrar(tipo, titulo, detalhe) {
  const area = areaDeToasts();
  let temporizador = null;
  let removido = false;

  const remover = () => {
    if (removido) return;
    removido = true;
    clearTimeout(temporizador);
    toast.setAttribute("data-saindo", "");
    setTimeout(() => toast.remove(), 220);
  };

  const agendar = () => {
    clearTimeout(temporizador);
    temporizador = setTimeout(remover, DURACAO[tipo]);
  };

  const toast = el(
    "div",
    { class: "toast", "data-tipo": tipo, role: tipo === "erro" ? "alert" : "status" },
    icone(ICONE[tipo]),
    el("div", { class: "toast-corpo" }, el("strong", {}, titulo), detalhe ? el("span", {}, detalhe) : null),
    el(
      "button",
      { type: "button", class: "toast-fechar", "aria-label": "Fechar notificação", onclick: remover },
      icone("fechar"),
    ),
  );

  toast.addEventListener("mouseenter", () => clearTimeout(temporizador));
  toast.addEventListener("mouseleave", agendar);
  toast.addEventListener("focusin", () => clearTimeout(temporizador));
  toast.addEventListener("focusout", agendar);

  while (area.children.length >= LIMITE) area.firstElementChild.remove();
  area.append(toast);
  agendar();
}

export const notificar = {
  ok: (titulo, detalhe) => mostrar("ok", titulo, detalhe),
  info: (titulo, detalhe) => mostrar("info", titulo, detalhe),
  erro: (titulo, detalhe) => mostrar("erro", titulo, detalhe),
};
