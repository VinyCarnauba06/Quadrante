export function confirmar({ titulo, texto, rotuloConfirmar = "Confirmar", perigo = false }) {
  const dialogo = document.getElementById("dialogo");
  const botaoConfirmar = document.getElementById("dialogo-confirmar");

  document.getElementById("dialogo-titulo").textContent = titulo;
  document.getElementById("dialogo-texto").textContent = texto;
  botaoConfirmar.textContent = rotuloConfirmar;
  botaoConfirmar.className = perigo ? "btn btn-perigo" : "btn btn-primario";

  return new Promise((resolver) => {
    const aoClicarFora = (evento) => {
      if (evento.target === dialogo) dialogo.close("cancelar");
    };

    const aoFechar = () => {
      dialogo.removeEventListener("close", aoFechar);
      dialogo.removeEventListener("click", aoClicarFora);
      resolver(dialogo.returnValue === "confirmar");
    };

    dialogo.returnValue = "";
    dialogo.addEventListener("close", aoFechar);
    dialogo.addEventListener("click", aoClicarFora);
    dialogo.showModal();
  });
}
