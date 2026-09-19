const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const PALAVRAS_MINUSCULAS = new Set(["de", "da", "do", "das", "dos", "e"]);

const MOTIVOS = {
  ferias: "Férias",
  falta: "Falta",
  licenca: "Licença",
  outro: "Outro",
};

export function nomeProprio(texto) {
  if (!texto) return "";
  return texto
    .toLowerCase()
    .split(/\s+/)
    .map((palavra, i) =>
      i > 0 && PALAVRAS_MINUSCULAS.has(palavra) ? palavra : palavra.charAt(0).toUpperCase() + palavra.slice(1),
    )
    .join(" ");
}

export function enderecoCurto(endereco) {
  return (endereco ?? "").replace(/,\s*Maceió\s*-\s*AL\s*$/i, "");
}

export function rotuloMotivo(chave) {
  return MOTIVOS[chave] ?? nomeProprio(chave);
}

export function dataCurta(iso) {
  const [ano, mes, dia] = iso.slice(0, 10).split("-").map(Number);
  if (!ano || !mes || !dia) return iso;
  return `${String(dia).padStart(2, "0")} ${MESES[mes - 1]}`;
}

export function dataParaCampo(data) {
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  const dia = String(data.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

export function distancia(metros) {
  if (metros < 1000) return `${Math.round(metros)} m`;
  return `${(metros / 1000).toFixed(1).replace(".", ",")} km`;
}

export function quilometros(km) {
  return Number(km).toFixed(1).replace(".", ",");
}

export function milissegundos(ms) {
  if (ms < 1) return "< 1 ms";
  if (ms < 100) return `${ms.toFixed(0)} ms`;
  return `${Math.round(ms)} ms`;
}

export function plural(quantidade, singular, pluralForma) {
  return `${quantidade} ${quantidade === 1 ? singular : pluralForma}`;
}
