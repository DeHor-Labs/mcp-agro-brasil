"""Provider ESALQ/B3 - indicador nacional de boi gordo.

Fonte: Notícias Agrícolas - https://www.noticiasagricolas.com.br/cotacoes/boi-gordo/boi-gordo-indicador-esalq-bmf
O indicador ESALQ/B3 é a referência nacional de precificação do boi gordo no Brasil.
"""

from __future__ import annotations

import re
from datetime import date

import httpx

_ESALQ_URL = "https://www.noticiasagricolas.com.br/cotacoes/boi-gordo/boi-gordo-indicador-esalq-bmf"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

_TIMEOUT = 15.0

# Padrão esperado na página: "à vista R$: 338,00" (com variações de espaço/case)
_PADRAO_A_VISTA = re.compile(
    r"à\s+vista\s+R\$\s*:\s*([\d.,]+)",
    re.IGNORECASE,
)


def _parse_valor(raw: str) -> float:
    """Converte string de valor monetário brasileiro para float."""
    limpo = raw.strip().replace(".", "").replace(",", ".")
    return float(limpo)


def buscar_indicador_esalq() -> dict[str, object]:
    """Busca o indicador nacional ESALQ/B3 de boi gordo.

    Returns:
        Dicionário com campos:
            fonte, a_vista, unidade, moeda, data_consulta.
            a_vista é None se o valor não for encontrado na página.

    Raises:
        httpx.HTTPError: Em caso de falha de rede ou HTTP não-200.
    """
    with httpx.Client(
        headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True
    ) as client:
        resposta = client.get(_ESALQ_URL)
        resposta.raise_for_status()
        html = resposta.text

    match = _PADRAO_A_VISTA.search(html)
    a_vista = _parse_valor(match.group(1)) if match else None

    return {
        "fonte": "ESALQ/B3 via Notícias Agrícolas",
        "fonte_url": _ESALQ_URL,
        "indicador": "Boi Gordo ESALQ/B3",
        "a_vista": a_vista,
        "unidade": "@",  # arroba (15 kg)
        "moeda": "BRL",
        "data_consulta": date.today().isoformat(),
    }
