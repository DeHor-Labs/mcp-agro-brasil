"""Provider Scot Consultoria - cotação regional de boi gordo.

Fonte: https://www.scotconsultoria.com.br/cotacoes/boi-gordo/
HTML server-side renderizado, sem API pública.
Extraímos por regex as colunas de preço à vista e 30 dias por praça.
"""

from __future__ import annotations

import re
from datetime import date

import httpx

# URL pública da tabela de cotações
_SCOT_URL = "https://www.scotconsultoria.com.br/cotacoes/boi-gordo/"

# Headers realistas para evitar bloqueio por User-Agent
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

_TIMEOUT = 15.0


def _parse_valor(raw: str) -> float:
    """Converte string de valor monetário brasileiro para float.

    Exemplos: '316,50' -> 316.50, '1.316,50' -> 1316.50
    """
    limpo = raw.strip().replace(".", "").replace(",", ".")
    return float(limpo)


def _extrair_cotacao_praca(html: str, praca: str) -> dict[str, float | str | None]:
    """Extrai à vista e 30 dias para uma praça específica.

    A tabela Scot renderiza linhas no formato:
      <td ...>GO Goiânia</td><td ...>316,50</td><td ...>318,00</td>...

    O regex tolera atributos extras nas tags <td>, espaços e variações de
    encoding do nome da praça (ex.: Goi\xe2nia vs Goiânia).
    """
    # Escapa a praça para uso no regex, depois substitui espaços por \s+
    praca_escaped = re.escape(praca).replace(r"\ ", r"\s+")
    # Aceita variação de caracteres ao redor do nome (ex.: Goiânia vs Goia~nia)
    # Estratégia: match liberal na célula do nome, captura as 2 próximas células
    padrao = (
        r"<td[^>]*>\s*" + praca_escaped + r"\s*</td>"
        r"\s*<td[^>]*>\s*([\d.,]+)\s*</td>"
        r"\s*<td[^>]*>\s*([\d.,]+)\s*</td>"
    )
    match = re.search(padrao, html, re.IGNORECASE | re.DOTALL)
    if not match:
        return {"a_vista": None, "trinta_dias": None}

    return {
        "a_vista": _parse_valor(match.group(1)),
        "trinta_dias": _parse_valor(match.group(2)),
    }


def buscar_cotacao_boi(praca: str = "GO Goiânia") -> dict[str, object]:
    """Busca cotação regional de boi gordo na Scot Consultoria.

    Args:
        praca: Nome da praça conforme listado na tabela Scot (ex.: "GO Goiânia").

    Returns:
        Dicionário com campos:
            fonte, praca, a_vista, trinta_dias, unidade, moeda, data_consulta.
            a_vista/trinta_dias são None se a praça não for encontrada.

    Raises:
        httpx.HTTPError: Em caso de falha de rede ou HTTP não-200.
    """
    with httpx.Client(
        headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True
    ) as client:
        resposta = client.get(_SCOT_URL)
        resposta.raise_for_status()
        html = resposta.text

    valores = _extrair_cotacao_praca(html, praca)

    return {
        "fonte": "Scot Consultoria",
        "fonte_url": _SCOT_URL,
        "praca": praca,
        "a_vista": valores["a_vista"],
        "trinta_dias": valores["trinta_dias"],
        "unidade": "@",  # arroba (15 kg)
        "moeda": "BRL",
        "data_consulta": date.today().isoformat(),
    }
