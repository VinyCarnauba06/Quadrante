export class ErroApi extends Error {
  constructor(mensagem, status) {
    super(mensagem);
    this.name = "ErroApi";
    this.status = status;
  }
}

const observadores = new Set();

export function aoMedir(observador) {
  observadores.add(observador);
}

function avisar(resultado) {
  observadores.forEach((observador) => observador(resultado));
}

async function requisitar(caminho, { metodo = "GET", corpo } = {}) {
  const inicio = performance.now();
  let resposta;
  try {
    resposta = await fetch(caminho, {
      method: metodo,
      headers: corpo === undefined ? undefined : { "Content-Type": "application/json" },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    });
  } catch {
    avisar({ ok: false, ms: performance.now() - inicio });
    throw new ErroApi("Sem conexão com o servidor. Confira se o Flask continua rodando.", 0);
  }

  const ms = performance.now() - inicio;
  let dados = null;
  try {
    dados = await resposta.json();
  } catch {
    dados = null;
  }

  if (!resposta.ok) {
    avisar({ ok: false, ms });
    throw new ErroApi(dados?.erro ?? `O servidor respondeu com erro ${resposta.status}.`, resposta.status);
  }

  avisar({ ok: true, ms });
  return { dados, ms };
}

export const api = {
  async get(caminho) {
    return (await requisitar(caminho)).dados;
  },
  async post(caminho, corpo = {}) {
    return (await requisitar(caminho, { metodo: "POST", corpo })).dados;
  },
  medido(caminho) {
    return requisitar(caminho);
  },
  postMedido(caminho, corpo = {}) {
    return requisitar(caminho, { metodo: "POST", corpo });
  },
};
