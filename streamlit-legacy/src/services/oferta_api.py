import os
import requests
from typing import Any, Dict

BASE = os.getenv("OFERTA_API_BASE_URL", "https://ofertafup.sistema.pro.br/api/oferta")
TIMEOUT = int(os.getenv("OFERTA_API_TIMEOUT", "10"))


class OfertaAPIError(Exception):
    pass


def fetch_ofertas(cod_semestre: str) -> Dict[str, Any]:
    """
    Fetch ofertas JSON from external API.

    Raises OfertaAPIError on non-200 or invalid payload.
    """
    url = f"{BASE}/{cod_semestre}"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise OfertaAPIError(
                "Resposta da API inesperada: payload não é um objeto JSON"
            )
        return data
    except requests.HTTPError as e:
        raise OfertaAPIError(f"HTTP error ao acessar {url}: {e}")
    except requests.RequestException as e:
        raise OfertaAPIError(f"Erro de conexão ao acessar {url}: {e}")
    except ValueError as e:
        raise OfertaAPIError(f"Resposta JSON inválida de {url}: {e}")
