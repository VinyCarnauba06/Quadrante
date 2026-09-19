import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

from backend.domain.geocodificacao import ResultadoGeocodificacao
from backend.service.geocoding_service import GeocodificacaoFalhouError, GeocodificacaoIndisponivelError

URL_BUSCA = "https://api.geoapify.com/v1/geocode/search"
CENTRO_MACEIO = (-9.6498, -35.7089)
RAIO_BUSCA_METROS = 30000


class GeoapifyGeocodificador:
    def __init__(
        self,
        chave: str,
        centro: tuple[float, float] = CENTRO_MACEIO,
        raio_metros: int = RAIO_BUSCA_METROS,
        timeout: float = 6.0,
        abrir: Callable = urllib.request.urlopen,
    ):
        self._chave = chave
        self._centro = centro
        self._raio_metros = raio_metros
        self._timeout = timeout
        self._abrir = abrir

    def buscar(self, texto: str, limite: int = 5) -> list[ResultadoGeocodificacao]:
        latitude, longitude = self._centro
        parametros = urllib.parse.urlencode(
            {
                "text": texto,
                "format": "json",
                "limit": limite,
                "lang": "pt",
                "filter": f"circle:{longitude},{latitude},{self._raio_metros}",
                "bias": f"proximity:{longitude},{latitude}",
                "apiKey": self._chave,
            }
        )
        try:
            with self._abrir(f"{URL_BUSCA}?{parametros}", timeout=self._timeout) as resposta:
                corpo = json.load(resposta)
        except urllib.error.HTTPError as erro:
            if erro.code in (401, 403):
                raise GeocodificacaoIndisponivelError("A chave da Geoapify foi recusada. Confira GEOAPIFY_API_KEY no .env.") from None
            if erro.code == 429:
                raise GeocodificacaoFalhouError("Limite de requisições da Geoapify atingido. Tente novamente em instantes.") from None
            raise GeocodificacaoFalhouError(f"A Geoapify respondeu com erro {erro.code}.") from None
        except (urllib.error.URLError, OSError, ValueError):
            raise GeocodificacaoFalhouError("Não foi possível falar com a Geoapify. Confira a conexão com a internet.") from None

        return [self._converter(item) for item in corpo.get("results") or [] if "lat" in item and "lon" in item]

    @staticmethod
    def _converter(item: dict) -> ResultadoGeocodificacao:
        ranking = item.get("rank") or {}
        return ResultadoGeocodificacao(
            endereco=item.get("formatted") or "",
            latitude=float(item["lat"]),
            longitude=float(item["lon"]),
            bairro=item.get("suburb") or item.get("district") or "",
            confianca=ranking.get("confidence"),
        )
