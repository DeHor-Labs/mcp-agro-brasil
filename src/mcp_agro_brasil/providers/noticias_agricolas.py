"""Provider Notícias Agrícolas - cotações de grãos via CEPEA/ESALQ.

Fonte: https://www.noticiasagricolas.com.br/cotacoes/
HTML server-side renderizado, sem API pública.

Produtos suportados:
- Soja: Indicador CEPEA/ESALQ Porto de Paranaguá (R$/saca 60 kg)
- Milho: Indicador CEPEA/ESALQ (R$/saca 60 kg)
- Leite: Preços ao produtor CEPEA por estado (R$/litro)

CEPEA direto (cepea.esalq.usp.br) não é usado: bloqueia 403 e a licença
CC BY-NC proíbe uso comercial. Notícias Agrícolas espelha os indicadores
publicamente sem essas restrições.
"""

from __future__ import annotations

import re
from datetime import date

import httpx

# ---------------------------------------------------------------------------
# URLs de cada indicador
# ---------------------------------------------------------------------------

_BASE = "https://www.noticiasagricolas.com.br/cotacoes"

_URL_SOJA = f"{_BASE}/soja/soja-indicador-cepea-esalq-porto-paranagua"
_URL_MILHO = f"{_BASE}/milho/indicador-cepea-esalq-milho"
_URL_LEITE = f"{_BASE}/leite/leite-precos-ao-produtor-cepea-rs-litro"

# Headers realistas para evitar bloqueio por User-Agent
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

# ---------------------------------------------------------------------------
# Padrões de regex
# ---------------------------------------------------------------------------

# Soja e milho: tabela com colunas data (dd/mm/yyyy) | valor | variação (%).
# Mesmo padrão do boi ESALQ; captura o valor da linha mais recente (primeiro tbody).
_PADRAO_DATA_VALOR = re.compile(
    r"<td>\d{2}/\d{2}/\d{4}</td>\s*<td>([\d.,]+)</td>",
    re.IGNORECASE | re.DOTALL,
)


def _parse_valor(raw: str) -> float:
    """Converte string de valor monetário brasileiro para float.

    Exemplos: '133,87' -> 133.87, '2,5169' -> 2.5169
    """
    limpo = raw.strip().replace(".", "").replace(",", ".")
    return float(limpo)


def _extrair_valor_estado_leite(html: str, estado: str) -> float | None:
    """Extrai preço de leite para um estado ou 'Brasil'.

    A tabela CEPEA leite renderiza linhas no formato:
      <td>GO</td><td>2,5894</td><td>+10,70</td>

    Aceita qualquer estado por sigla de 2 letras ou 'Brasil'.
    """
    padrao = re.compile(
        r"<td>\s*" + re.escape(estado) + r"\s*</td>\s*<td>\s*([\d.,]+)\s*</td>",
        re.IGNORECASE | re.DOTALL,
    )
    match = padrao.search(html)
    return _parse_valor(match.group(1)) if match else None


# ---------------------------------------------------------------------------
# Funções públicas de busca
# ---------------------------------------------------------------------------


def buscar_cotacao_soja() -> dict[str, object]:
    """Busca o indicador CEPEA/ESALQ de soja - Porto de Paranaguá.

    Returns:
        Dicionário com campos:
            fonte, fonte_url, indicador, a_vista, unidade, moeda, data_consulta.
            a_vista é None se o valor não for encontrado na página.

    Raises:
        httpx.HTTPError: Em caso de falha de rede ou HTTP não-200.
    """
    with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
        resposta = client.get(_URL_SOJA)
        resposta.raise_for_status()
        html = resposta.text

    match = _PADRAO_DATA_VALOR.search(html)
    a_vista = _parse_valor(match.group(1)) if match else None

    return {
        "fonte": "CEPEA/ESALQ via Notícias Agrícolas",
        "fonte_url": _URL_SOJA,
        "indicador": "Soja CEPEA/ESALQ - Porto de Paranaguá",
        "a_vista": a_vista,
        "unidade": "saca",  # saca de 60 kg
        "moeda": "BRL",
        "data_consulta": date.today().isoformat(),
    }


def buscar_cotacao_milho() -> dict[str, object]:
    """Busca o indicador CEPEA/ESALQ de milho.

    Returns:
        Dicionário com campos:
            fonte, fonte_url, indicador, a_vista, unidade, moeda, data_consulta.
            a_vista é None se o valor não for encontrado na página.

    Raises:
        httpx.HTTPError: Em caso de falha de rede ou HTTP não-200.
    """
    with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
        resposta = client.get(_URL_MILHO)
        resposta.raise_for_status()
        html = resposta.text

    match = _PADRAO_DATA_VALOR.search(html)
    a_vista = _parse_valor(match.group(1)) if match else None

    return {
        "fonte": "CEPEA/ESALQ via Notícias Agrícolas",
        "fonte_url": _URL_MILHO,
        "indicador": "Milho CEPEA/ESALQ",
        "a_vista": a_vista,
        "unidade": "saca",  # saca de 60 kg
        "moeda": "BRL",
        "data_consulta": date.today().isoformat(),
    }


def buscar_cotacao_leite(estado: str = "Brasil") -> dict[str, object]:
    """Busca preço ao produtor de leite (CEPEA RS) por estado.

    Args:
        estado: Sigla do estado (ex.: 'GO', 'MG', 'SP') ou 'Brasil' para média nacional.
                Padrão: 'Brasil'.

    Returns:
        Dicionário com campos:
            fonte, fonte_url, indicador, estado, a_vista, unidade, moeda, data_consulta.
            a_vista é None se o estado não for encontrado na tabela.

    Raises:
        httpx.HTTPError: Em caso de falha de rede ou HTTP não-200.
    """
    with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
        resposta = client.get(_URL_LEITE)
        resposta.raise_for_status()
        html = resposta.text

    a_vista = _extrair_valor_estado_leite(html, estado)

    return {
        "fonte": "CEPEA via Notícias Agrícolas",
        "fonte_url": _URL_LEITE,
        "indicador": "Leite ao Produtor CEPEA",
        "estado": estado,
        "a_vista": a_vista,
        "unidade": "L",  # R$/litro
        "moeda": "BRL",
        "data_consulta": date.today().isoformat(),
    }
