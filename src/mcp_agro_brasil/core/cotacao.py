"""Orquestração de cotações com cache diário e fallback.

Fluxo:
  1. Tenta provider regional (Scot) para a praça solicitada.
  2. Se falhar ou retornar None, usa fallback nacional (ESALQ).
  3. Nunca inventa valor: se ambos falharem, retorna erro claro.

Cache: em memória, TTL de 4 horas. Evita bater na mesma fonte repetidamente
durante uma sessão Claude sem perder frescor dos dados intraday.
"""

from __future__ import annotations

import time
from typing import Any

from mcp_agro_brasil.providers import esalq, scot

# ---------------------------------------------------------------------------
# Cache em memória simples
# ---------------------------------------------------------------------------

_CACHE: dict[str, dict[str, Any]] = {}
_TTL_SEGUNDOS = 4 * 60 * 60  # 4 horas


def _cache_key(praca: str) -> str:
    return f"cotacao:boi:{praca.lower().strip()}"


def _cache_get(key: str) -> dict[str, Any] | None:
    entrada = _CACHE.get(key)
    if entrada is None:
        return None
    if time.monotonic() - entrada["ts"] > _TTL_SEGUNDOS:
        del _CACHE[key]
        return None
    return entrada["data"]


def _cache_set(key: str, data: dict[str, Any]) -> None:
    _CACHE[key] = {"ts": time.monotonic(), "data": data}


# ---------------------------------------------------------------------------
# Praças disponíveis na Scot (expandir conforme validação)
# ---------------------------------------------------------------------------

PRACAS_SCOT: list[str] = [
    "GO Goiânia",
    "MS Campo Grande",
    "MT Cuiabá",
    "MG Belo Horizonte",
    "SP Araçatuba",
    "SP Barretos",
    "SP Presidente Prudente",
    "SP São José do Rio Preto",
    "PR Cascavel",
    "RS Porto Alegre",
    "PA Redenção",
    "BA Feira de Santana",
]


def cotacao_boi_gordo(praca: str = "GO Goiânia") -> dict[str, Any]:
    """Retorna cotação de boi gordo para a praça solicitada.

    Tenta Scot (regional) primeiro. Se o valor à vista for None ou ocorrer
    erro de rede, faz fallback para o indicador nacional ESALQ/B3.

    Args:
        praca: Praça de referência (ex.: "GO Goiânia"). Padrão: "GO Goiânia".

    Returns:
        Dicionário padronizado com:
            praca, a_vista, trinta_dias, unidade, moeda, fonte,
            fonte_url, data_consulta, fallback (bool).

    Raises:
        RuntimeError: Se todos os providers falharam sem retornar valor.
    """
    chave = _cache_key(praca)
    cached = _cache_get(chave)
    if cached is not None:
        return {**cached, "cache_hit": True}

    erros: list[str] = []
    resultado: dict[str, Any] | None = None
    usou_fallback = False

    # --- Provider primário: Scot ---
    try:
        dados = scot.buscar_cotacao_boi(praca)
        if dados.get("a_vista") is not None:
            resultado = {
                "praca": praca,
                "a_vista": dados["a_vista"],
                "trinta_dias": dados.get("trinta_dias"),
                "unidade": dados["unidade"],
                "moeda": dados["moeda"],
                "fonte": dados["fonte"],
                "fonte_url": dados["fonte_url"],
                "data_consulta": dados["data_consulta"],
                "fallback": False,
                "cache_hit": False,
            }
        else:
            erros.append(f"Scot: praça '{praca}' não encontrada na tabela")
    except Exception as exc:
        erros.append(f"Scot: {exc}")

    # --- Fallback: ESALQ ---
    if resultado is None:
        usou_fallback = True
        try:
            dados_esalq = esalq.buscar_indicador_esalq()
            if dados_esalq.get("a_vista") is not None:
                resultado = {
                    "praca": "Nacional (ESALQ/B3)",
                    "a_vista": dados_esalq["a_vista"],
                    "trinta_dias": None,
                    "unidade": dados_esalq["unidade"],
                    "moeda": dados_esalq["moeda"],
                    "fonte": dados_esalq["fonte"],
                    "fonte_url": dados_esalq["fonte_url"],
                    "data_consulta": dados_esalq["data_consulta"],
                    "fallback": True,
                    "cache_hit": False,
                    "aviso": (
                        f"Praça '{praca}' indisponível via Scot. "
                        "Retornando indicador nacional ESALQ/B3."
                    ),
                }
            else:
                erros.append("ESALQ: valor à vista não encontrado na página")
        except Exception as exc:
            erros.append(f"ESALQ: {exc}")

    if resultado is None:
        raise RuntimeError(
            f"Todos os providers falharam ao buscar cotação de boi gordo. "
            f"Erros: {'; '.join(erros)}"
        )

    _ = usou_fallback  # informação está em resultado["fallback"]
    _cache_set(chave, resultado)
    return resultado


def indicador_esalq() -> dict[str, Any]:
    """Retorna o indicador nacional ESALQ/B3 diretamente, com cache.

    Returns:
        Dicionário com: indicador, a_vista, unidade, moeda, fonte,
        fonte_url, data_consulta, cache_hit.

    Raises:
        RuntimeError: Se o provider ESALQ falhar.
    """
    chave = "esalq:boi:nacional"
    cached = _cache_get(chave)
    if cached is not None:
        return {**cached, "cache_hit": True}

    try:
        dados = esalq.buscar_indicador_esalq()
    except Exception as exc:
        raise RuntimeError(f"Falha ao buscar indicador ESALQ: {exc}") from exc

    resultado = {**dados, "cache_hit": False}
    _cache_set(chave, resultado)
    return resultado
