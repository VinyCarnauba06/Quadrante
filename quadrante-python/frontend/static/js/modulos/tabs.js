export function abrirAba(id) {
  document.getElementById(`tab-${id}`)?.click();
}

export function iniciarTabs() {
  const abas = [...document.querySelectorAll('[role="tab"]')];

  function abrir(aba, { foco = false } = {}) {
    abas.forEach((atual) => {
      const selecionada = atual === aba;
      atual.setAttribute("aria-selected", String(selecionada));
      atual.tabIndex = selecionada ? 0 : -1;
      document.getElementById(atual.getAttribute("aria-controls")).hidden = !selecionada;
    });
    if (foco) aba.focus();
  }

  abas.forEach((aba, indice) => {
    aba.addEventListener("click", () => abrir(aba));
    aba.addEventListener("keydown", (evento) => {
      let alvo = null;
      if (evento.key === "ArrowRight") alvo = abas[(indice + 1) % abas.length];
      else if (evento.key === "ArrowLeft") alvo = abas[(indice - 1 + abas.length) % abas.length];
      else if (evento.key === "Home") alvo = abas[0];
      else if (evento.key === "End") alvo = abas[abas.length - 1];
      if (alvo) {
        evento.preventDefault();
        abrir(alvo, { foco: true });
      }
    });
  });
}
