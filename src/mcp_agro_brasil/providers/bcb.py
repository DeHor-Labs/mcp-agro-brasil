"""Provider Banco Central do Brasil - PTAX (cotação oficial do dólar).

Fonte: API Olinda BCB - https://olinda.bcb.gov.br/
API JSON aberta, gratuita, sem autenticação.
Endpoint: CotacaoDolarDia - cotação PTAX de fechamento do dia útil.

PTAX é a taxa de câmbio oficial divulgada pelo Banco Central, referência
para contratos de câmbio, operações de balancete e conversões tributárias.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx

_BCB_URL = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"
    "/CotacaoDolarDia(dataCotacao=@dataCotacao)"
)

_TIMEOUT = 15.0

# Máximo de dias úteis para retroceder buscando cotação (cobre fins de semana + feriados)
_MAX_DIAS_RETROATIVOS = 7


def buscar_ptax() -> dict[str, Any]:
    """Busca a cotação PTAX mais recente do dólar americano (USD/BRL).

    Tenta a data de hoje e, se não houver cotação (fim de semana ou feriado),
    retrocede até encontrar o último dia útil com PTAX disponível.

    Returns:
        Dicionário com campos:
            fonte, moeda_origem, moeda_destino, compra, venda,
            data_hora_cotacao, data_consulta.

    Raises:
        RuntimeError: Se não encontrar PTAX nos últimos dias retroativos.
        httpx.HTTPError: Em caso de falha de rede ou HTTP não-200.
    """
    for delta in range(_MAX_DIAS_RETROATIVOS):
        d = date.today() - timedelta(days=delta)
        # A API espera o formato MM-DD-YYYY
        data_fmt = d.strftime("%m-%d-%Y")

        params = {
            "@dataCotacao": f"'{data_fmt}'",
            "$top": "1",
            "$format": "json",
        }
        with httpx.Client(timeout=_TIMEOUT) as client:
            resposta = client.get(_BCB_URL, params=params)
            resposta.raise_for_status()
            dados = resposta.json()

        valores = dados.get("value", [])
        if valores:
            cotacao = valores[0]
            return {
                "fonte": "Banco Central do Brasil (PTAX)",
                "fonte_url": "https://www.bcb.gov.br/estabilidadefinanceira/historicocotacoes",
                "moeda_origem": "USD",
                "moeda_destino": "BRL",
                "compra": float(cotacao["cotacaoCompra"]),
                "venda": float(cotacao["cotacaoVenda"]),
                "data_hora_cotacao": cotacao["dataHoraCotacao"],
                "data_consulta": date.today().isoformat(),
            }

    raise RuntimeError(
        f"PTAX indisponível: nenhuma cotação encontrada nos últimos {_MAX_DIAS_RETROATIVOS} dias."
    )
