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

from mcp_agro_brasil.providers import (
    bcb,
    comex_stat,
    esalq,
    noticias_agricolas,
    open_meteo,
    rss_agro,
    scot,
)

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
            f"Todos os providers falharam ao buscar cotação de boi gordo. Erros: {'; '.join(erros)}"
        )

    _ = usou_fallback  # informação está em resultado["fallback"]
    _cache_set(chave, resultado)
    return resultado


# ---------------------------------------------------------------------------
# Produtos disponíveis (expandir conforme novos providers)
# ---------------------------------------------------------------------------

PRODUTOS_DISPONIVEIS: list[str] = [
    "boi_gordo",
    "soja",
    "milho",
    "leite",
    "clima",
    "cambio_dolar",
    "exportacao_agro",
    "noticias_agro",
]

ESTADOS_LEITE: list[str] = [
    "RS",
    "SC",
    "PR",
    "SP",
    "MG",
    "GO",
    "BA",
    "RJ",
    "ES",
    "Brasil",
]


# ---------------------------------------------------------------------------
# Grãos: Soja, Milho, Leite
# ---------------------------------------------------------------------------


def cotacao_soja() -> dict[str, Any]:
    """Retorna o indicador CEPEA/ESALQ de soja - Porto de Paranaguá, com cache.

    Returns:
        Dicionário com: indicador, a_vista, unidade, moeda, fonte,
        fonte_url, data_consulta, cache_hit.

    Raises:
        RuntimeError: Se o provider falhar.
    """
    chave = "graos:soja:cepea"
    cached = _cache_get(chave)
    if cached is not None:
        return {**cached, "cache_hit": True}

    try:
        dados = noticias_agricolas.buscar_cotacao_soja()
    except Exception as exc:
        raise RuntimeError(f"Falha ao buscar cotação de soja: {exc}") from exc

    resultado = {**dados, "cache_hit": False}
    _cache_set(chave, resultado)
    return resultado


def cotacao_milho() -> dict[str, Any]:
    """Retorna o indicador CEPEA/ESALQ de milho, com cache.

    Returns:
        Dicionário com: indicador, a_vista, unidade, moeda, fonte,
        fonte_url, data_consulta, cache_hit.

    Raises:
        RuntimeError: Se o provider falhar.
    """
    chave = "graos:milho:cepea"
    cached = _cache_get(chave)
    if cached is not None:
        return {**cached, "cache_hit": True}

    try:
        dados = noticias_agricolas.buscar_cotacao_milho()
    except Exception as exc:
        raise RuntimeError(f"Falha ao buscar cotação de milho: {exc}") from exc

    resultado = {**dados, "cache_hit": False}
    _cache_set(chave, resultado)
    return resultado


def cotacao_leite(estado: str = "Brasil") -> dict[str, Any]:
    """Retorna preço ao produtor de leite CEPEA por estado, com cache.

    Args:
        estado: Sigla do estado (ex.: 'GO', 'MG', 'SP') ou 'Brasil'.
                Padrão: 'Brasil'.

    Returns:
        Dicionário com: indicador, estado, a_vista, unidade, moeda, fonte,
        fonte_url, data_consulta, cache_hit.

    Raises:
        RuntimeError: Se o provider falhar.
    """
    chave = f"graos:leite:{estado.lower().strip()}"
    cached = _cache_get(chave)
    if cached is not None:
        return {**cached, "cache_hit": True}

    try:
        dados = noticias_agricolas.buscar_cotacao_leite(estado)
    except Exception as exc:
        raise RuntimeError(f"Falha ao buscar cotação de leite: {exc}") from exc

    resultado = {**dados, "cache_hit": False}
    _cache_set(chave, resultado)
    return resultado


def clima_previsao(cidade: str, dias: int = 5) -> dict[str, Any]:
    """Retorna previsão do tempo para uma cidade brasileira, com cache de 1 hora.

    Args:
        cidade: Nome da cidade (ex.: "Goiânia", "Sorriso MT", "Uberaba").
        dias: Número de dias de previsão (1 a 7). Padrão: 5.

    Returns:
        Dicionário com: fonte, cidade, cidade_resolvida, dias (lista), data_consulta.
        Cada dia contém: data, temp_max_c, temp_min_c, precipitacao_mm, prob_chuva_pct.

    Raises:
        ValueError: Cidade não encontrada na API de geocoding.
        RuntimeError: Se o provider falhar.
    """
    dias = max(1, min(dias, 7))
    chave = f"clima:{cidade.lower().strip()}:{dias}"
    cached = _cache_get(chave)
    if cached is not None:
        return {**cached, "cache_hit": True}

    try:
        dados = open_meteo.buscar_previsao(cidade, dias)
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Falha ao buscar previsão do tempo: {exc}") from exc

    resultado = {**dados, "cache_hit": False}
    # TTL diferenciado: clima muda menos que cotação, 1 hora é suficiente
    _CACHE[f"clima:{cidade.lower().strip()}:{dias}"] = {
        "ts": time.monotonic(),
        "data": resultado,
    }
    return resultado


_TTL_CAMBIO_SEGUNDOS = 4 * 60 * 60  # 4 horas (PTAX é divulgado 1x ao dia)


def cambio_dolar() -> dict[str, Any]:
    """Retorna a cotação PTAX oficial do dólar (USD/BRL), com cache de 4 horas.

    Usa a API Olinda do Banco Central do Brasil. Se hoje não tiver PTAX
    (fim de semana ou feriado), retorna o último dia útil disponível.

    Returns:
        Dicionário com: fonte, moeda_origem, moeda_destino, compra, venda,
        data_hora_cotacao, data_consulta, cache_hit.

    Raises:
        RuntimeError: Se o provider BCB falhar ou não houver cotação recente.
    """
    chave = "cambio:usd:ptax"
    cached = _cache_get(chave)
    if cached is not None:
        return {**cached, "cache_hit": True}

    try:
        dados = bcb.buscar_ptax()
    except Exception as exc:
        raise RuntimeError(f"Falha ao buscar câmbio PTAX: {exc}") from exc

    resultado = {**dados, "cache_hit": False}
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


# ---------------------------------------------------------------------------
# Exportação agro (Comex Stat / MDIC)
# ---------------------------------------------------------------------------

_TTL_EXPORTACAO_SEGUNDOS = 24 * 60 * 60  # 1 dia (dados mensais, mudam raramente)


def exportacao_agro(produto: str) -> dict[str, Any]:
    """Retorna dados de exportação para um produto do agronegócio, com cache de 1 dia.

    Usa a API pública Comex Stat do MDIC. Dados mensais com defasagem de 1-2 meses.

    Args:
        produto: Identificador do produto. Aceitos: "soja", "carne_bovina", "milho".

    Returns:
        Dicionário com: fonte, produto, ncms, periodo, ano, mes,
        fob_usd, peso_kg, peso_ton, data_consulta, cache_hit.

    Raises:
        ValueError: Produto desconhecido.
        RuntimeError: Se o provider falhar ou não houver dados.
    """
    chave = f"exportacao:{produto.lower().strip()}"
    cached = _cache_get(chave)
    if cached is not None:
        return {**cached, "cache_hit": True}

    try:
        dados = comex_stat.buscar_exportacao(produto)
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Falha ao buscar exportação de '{produto}': {exc}") from exc

    resultado = {**dados, "cache_hit": False}
    _CACHE[chave] = {"ts": time.monotonic(), "data": resultado}
    return resultado


# ---------------------------------------------------------------------------
# Notícias do agronegócio (RSS)
# ---------------------------------------------------------------------------

_TTL_NOTICIAS_SEGUNDOS = 30 * 60  # 30 minutos


def noticias_agro(tema: str | None = None, limite: int = 5) -> dict[str, Any]:
    """Retorna as últimas notícias do agronegócio, com cache de 30 minutos.

    Args:
        tema: Palavra-chave para filtrar títulos (ex: "soja", "boi gordo").
              None para retornar as mais recentes sem filtro.
        limite: Número máximo de notícias (padrão: 5, máximo: 20).

    Returns:
        Dicionário com: fonte, feeds_consultados, tema_filtro, total,
        noticias (lista), data_consulta, cache_hit.
        Cada notícia contém: titulo, link, data, descricao, fonte.

    Raises:
        RuntimeError: Se todos os feeds RSS falharem.
    """
    tema_norm = tema.lower().strip() if tema else None
    chave = f"noticias:rss:{tema_norm or 'todas'}:{limite}"
    entrada = _CACHE.get(chave)
    if (
        entrada is not None
        and time.monotonic() - entrada["ts"] <= _TTL_NOTICIAS_SEGUNDOS
    ):
        return {**entrada["data"], "cache_hit": True}

    try:
        dados = rss_agro.buscar_noticias(tema=tema, limite=limite)
    except Exception as exc:
        raise RuntimeError(f"Falha ao buscar notícias: {exc}") from exc

    resultado = {**dados, "cache_hit": False}
    _CACHE[chave] = {"ts": time.monotonic(), "data": resultado}
    return resultado
