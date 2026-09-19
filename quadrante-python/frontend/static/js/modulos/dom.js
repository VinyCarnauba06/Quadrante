export function el(tag, atributos = {}, ...filhos) {
  const no = document.createElement(tag);
  for (const [chave, valor] of Object.entries(atributos)) {
    if (valor === null || valor === undefined || valor === false) continue;
    if (chave === "class") {
      no.className = valor;
    } else if (chave === "estilo") {
      for (const [propriedade, conteudo] of Object.entries(valor)) {
        no.style.setProperty(propriedade, conteudo);
      }
    } else if (chave.startsWith("on") && typeof valor === "function") {
      no.addEventListener(chave.slice(2).toLowerCase(), valor);
    } else {
      no.setAttribute(chave, valor === true ? "" : String(valor));
    }
  }
  for (const filho of filhos.flat(Infinity)) {
    if (filho === null || filho === undefined || filho === false) continue;
    no.append(filho instanceof Node ? filho : document.createTextNode(String(filho)));
  }
  return no;
}

export function limpar(no) {
  no.replaceChildren();
  return no;
}

export function esqueletos(quantidade, classe = "fiscal-esqueleto") {
  return Array.from({ length: quantidade }, () => el("div", { class: `esqueleto ${classe}` }));
}

export async function comCarregando(botao, tarefa) {
  if (botao.getAttribute("aria-busy") === "true") return undefined;
  botao.setAttribute("aria-busy", "true");
  const iconeOriginal = botao.querySelector(".icone");
  const spinner = el("span", { class: "spinner", "aria-hidden": "true" });
  if (iconeOriginal) iconeOriginal.replaceWith(spinner);
  else botao.prepend(spinner);
  try {
    return await tarefa();
  } finally {
    if (iconeOriginal) spinner.replaceWith(iconeOriginal);
    else spinner.remove();
    botao.removeAttribute("aria-busy");
  }
}

export function desabilitar(botao, desabilitado, dica = "") {
  botao.setAttribute("aria-disabled", String(desabilitado));
  if (dica) botao.title = desabilitado ? dica : "";
}

export function estaDesabilitado(botao) {
  return botao.getAttribute("aria-disabled") === "true";
}
