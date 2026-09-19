import { fiscaisDeCampo } from "./estado.js";

const PALETA = [
  "#b84a00",
  "#0072b2",
  "#00805a",
  "#b8347a",
  "#6f42b5",
  "#8a6700",
  "#007a87",
  "#b2182b",
  "#4c6a2f",
  "#3d5a80",
];

export const COR_COORDENADOR = "#7c8580";

export function corDoFiscal(fiscal) {
  if (!fiscal || fiscal.papel !== "fiscal_campo") return COR_COORDENADOR;
  const indice = fiscaisDeCampo().findIndex((f) => f.id === fiscal.id);
  return PALETA[Math.max(indice, 0) % PALETA.length];
}
