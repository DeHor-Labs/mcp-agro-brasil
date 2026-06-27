"""Provider Comex Stat / MDIC - dados de exportação do agronegócio brasileiro.

Fonte: https://comexstat.mdic.gov.br/
API JSON pública do Ministério do Desenvolvimento, Indústria, Comércio e Serviços.
Sem autenticação. POST com filtros de período, NCM e métricas.

Produtos mapeados (NCM 8 dígitos):
- Soja em grão:             12019000 - "Soja, mesmo triturada, exceto para semeadura"
- Carne bovina congelada:   02023000 - "Carnes desossadas de bovino, congeladas"
- Carne bovina resfriada:   02013000 - "Carnes desossadas de bovino, frescas ou refrigeradas"
- Milho em grão:            10059010 - "Milho em grão, exceto para semeadura"

Métricas retornadas:
- metricFOB: valor exportado em USD (Free On Board)
- metricKG:  peso exportado em quilogramas
"""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx

_API_URL = "https://api-comexstat.mdic.gov.br/general"
_TIMEOUT = 20.0

# Mapeamento produto -> NCMs relevantes (lista para somar congelado + resfriado na carne bovina)
_PRODUTOS: dict[str, dict[str, Any]] = {
    "soja": {
        "ncms": ["12019000"],
        "nome": "Soja em grão",
        "descricao": "Soja, mesmo triturada, exceto para semeadura",
    },
    "carne_bovina": {
        "ncms": ["02023000", "02013000"],
        "nome": "Carne bovina",
        "descricao": "Carnes desossadas de bovino (congeladas + frescas/refrigeradas)",
    },
    "milho": {
        "ncms": ["10059010"],
        "nome": "Milho em grão",
        "descricao": "Milho em grão, exceto para semeadura",
    },
}

PRODUTOS_EXPORTACAO: list[str] = list(_PRODUTOS.keys())

# Máximo de meses para retroceder buscando o período mais recente com dados
_MAX_MESES_RETROATIVOS = 6


def _periodo_mais_recente() -> str:
    """Retorna o ano-mês mais recente com dados disponíveis no Comex Stat.

    O MDIC publica dados com defasagem de 1-2 meses. Tenta o mês anterior
    ao atual e retrocede até encontrar dados não vazios.

    Returns:
        String no formato "YYYY-MM" do mês com dados disponíveis.

    Raises:
        RuntimeError: Se não encontrar dados nos últimos _MAX_MESES_RETROATIVOS.
    """
    hoje = date.today()
    # Começa pelo mês anterior (dado mais recente costuma ter defasagem de 1-2 meses)
    ano, mes = hoje.year, hoje.month - 1
    if mes == 0:
        ano -= 1
        mes = 12

    for _ in range(_MAX_MESES_RETROATIVOS):
        periodo = f"{ano}-{mes:02d}"
        payload = {
            "flow": "export",
            "monthDetail": True,
            "period": {"from": periodo, "to": periodo},
            "filters": [{"filter": "chapter", "values": ["12"]}],
            "details": ["chapter"],
            "metrics": ["metricFOB"],
        }
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(_API_URL, json=payload)
            resp.raise_for_status()
            dados = resp.json()

        if dados.get("data", {}).get("list"):
            return periodo

        # Retrocede um mês
        mes -= 1
        if mes == 0:
            ano -= 1
            mes = 12

    raise RuntimeError(
        f"Comex Stat: nenhum dado encontrado nos últimos {_MAX_MESES_RETROATIVOS} meses."
    )


def _buscar_exportacao_ncms(ncms: list[str], periodo: str) -> list[dict[str, Any]]:
    """Busca dados de exportação para uma lista de NCMs em um período.

    Args:
        ncms: Lista de códigos NCM de 8 dígitos.
        periodo: Período no formato "YYYY-MM".

    Returns:
        Lista de registros da API com os campos coNcm, ncm, metricFOB, metricKG.

    Raises:
        httpx.HTTPError: Em caso de falha de rede ou HTTP não-200.
    """
    payload = {
        "flow": "export",
        "monthDetail": True,
        "period": {"from": periodo, "to": periodo},
        "filters": [{"filter": "ncm", "values": ncms}],
        "details": ["ncm"],
        "metrics": ["metricFOB", "metricKG"],
    }
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(_API_URL, json=payload)
        resp.raise_for_status()
        dados = resp.json()

    return dados.get("data", {}).get("list", [])


def buscar_exportacao(produto: str) -> dict[str, Any]:
    """Busca dados de exportação para um produto do agronegócio.

    Usa o período mais recente disponível no Comex Stat. Para carne bovina,
    soma os valores de congelada e fresca/refrigerada.

    Args:
        produto: Identificador do produto. Valores aceitos: "soja", "carne_bovina", "milho".

    Returns:
        Dicionário com campos:
            fonte, fonte_url, produto, ncms, periodo, ano, mes,
            fob_usd (USD FOB total), peso_kg (kg total),
            peso_ton (toneladas), data_consulta.

    Raises:
        ValueError: Produto desconhecido.
        RuntimeError: Se não houver dados disponíveis.
        httpx.HTTPError: Em caso de falha de rede.
    """
    produto_lower = produto.lower().strip()
    if produto_lower not in _PRODUTOS:
        validos = ", ".join(PRODUTOS_EXPORTACAO)
        raise ValueError(f"Produto '{produto}' desconhecido. Valores aceitos: {validos}.")

    info = _PRODUTOS[produto_lower]
    periodo = _periodo_mais_recente()
    registros = _buscar_exportacao_ncms(info["ncms"], periodo)

    # Soma FOB e KG de todos os NCMs do produto (ex: carne congelada + resfriada)
    fob_total = sum(int(r.get("metricFOB", 0)) for r in registros)
    kg_total = sum(int(r.get("metricKG", 0)) for r in registros)

    if fob_total == 0 and kg_total == 0:
        raise RuntimeError(
            f"Comex Stat: nenhum dado de exportação encontrado para '{produto}' "
            f"no período {periodo}."
        )

    ano_str, mes_str = periodo.split("-")

    return {
        "fonte": "Comex Stat / MDIC",
        "fonte_url": "https://comexstat.mdic.gov.br/",
        "produto": info["nome"],
        "descricao": info["descricao"],
        "ncms": info["ncms"],
        "periodo": periodo,
        "ano": int(ano_str),
        "mes": int(mes_str),
        "fob_usd": fob_total,
        "peso_kg": kg_total,
        "peso_ton": round(kg_total / 1000, 2),
        "data_consulta": date.today().isoformat(),
    }
