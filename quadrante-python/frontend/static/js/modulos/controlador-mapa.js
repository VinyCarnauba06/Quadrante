import { corDoFiscal } from "./cores.js";
import { assinar, estado, fiscaisDeCampo, fiscalPorId } from "./estado.js";
import { milissegundos, nomeProprio, plural, quilometros } from "./formatacao.js";
import { desenharGeral, desenharRota, destacarFiscal, iniciarMapa } from "./mapa.js";
import { selecionar } from "./servicos.js";

function definirCartao(titulo, subtitulo, mostrarVoltar) {
  document.getElementById("titulo-mapa").textContent = titulo;
  document.getElementById("subtitulo-mapa").textContent = subtitulo;
  document.getElementById("btn-mapa-geral").hidden = !mostrarVoltar;
}

function renderizar() {
  const carregando = document.getElementById("mapa-carregando");
  carregando.hidden = !estado.carregandoRota;
  if (estado.carregandoRota || !estado.mapaGeral) return;

  const fiscal = fiscalPorId(estado.selecionadoId);

  if (fiscal && fiscal.papel === "fiscal_campo" && estado.rota) {
    const paradas = estado.rota.paradas.filter((p) => p.latitude != null && p.longitude != null);
    const cor = corDoFiscal(fiscal);
    desenharRota({ paradas, cor, geral: estado.mapaGeral });
    const origem = estado.rota.doCache ? "instantâneo, em cache" : milissegundos(estado.rota.ms);
    definirCartao(
      `Rota de ${nomeProprio(fiscal.nome)}`,
      `${quilometros(estado.rota.distancia_total_km)} km · ${plural(paradas.length, "parada", "paradas")} · ${origem}`,
      estado.usuario?.papel !== "fiscal_campo",
    );
    return;
  }

  desenharGeral(estado.mapaGeral, corDoFiscalDoMapa);

  if (fiscal) {
    destacarFiscal(fiscal.id);
    definirCartao(`Carteira de ${nomeProprio(fiscal.nome)}`, "Coordenador · carteira fixa, fora de rotas", true);
    return;
  }

  const total = estado.mapaGeral.fiscais.reduce((soma, f) => soma + f.condominios.length, 0);
  definirCartao(
    "Mapa geral",
    `${plural(total, "condomínio", "condomínios")} · ${plural(fiscaisDeCampo().length, "fiscal de campo", "fiscais de campo")}`,
    false,
  );
}

function corDoFiscalDoMapa(fiscalDoMapa) {
  return corDoFiscal(fiscalPorId(fiscalDoMapa.id));
}

export function iniciarControladorMapa() {
  const elemento = document.getElementById("mapa");
  iniciarMapa(elemento, {
    chaveGeoapify: elemento.dataset.geoapifyChave ?? null,
    aoMudarBase: (disponivel) => {
      document.getElementById("mapa-aviso").hidden = disponivel;
    },
  });
  assinar("mapa", renderizar);
  assinar("rota", renderizar);
  document.getElementById("btn-mapa-geral").addEventListener("click", () => selecionar(null));
}
