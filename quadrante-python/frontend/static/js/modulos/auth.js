import { api } from "./api.js";
import { emitir, estado } from "./estado.js";

export async function obterUsuarioAtual() {
  const resposta = await api.get("/api/auth/me");
  estado.usuario = resposta.autenticado ? resposta.usuario : null;
  emitir("usuario");
  return estado.usuario;
}

export async function obterContasDemo() {
  return await api.get("/api/auth/contas-demo");
}

export async function fazerLogin(email, senha) {
  const resposta = await api.post("/api/auth/login", { email, senha });
  estado.usuario = resposta.usuario;
  emitir("usuario");
  return resposta.usuario;
}

export async function fazerLogout() {
  await api.post("/api/auth/logout");
  estado.usuario = null;
  emitir("usuario");
}
