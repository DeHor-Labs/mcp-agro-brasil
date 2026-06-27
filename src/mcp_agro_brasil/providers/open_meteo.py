"""Provider Open-Meteo - previsão do tempo sem token.

Fonte: https://open-meteo.com/
API JSON aberta, gratuita, sem autenticação.
Geocoding: https://geocoding-api.open-meteo.com/v1/search
Previsão: https://api.open-meteo.com/v1/forecast
"""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx

_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_TIMEOUT = 15.0


def _buscar_coordenadas(cidade: str) -> dict[str, float | str]:
    """Resolve nome de cidade brasileira para latitude/longitude.

    Args:
        cidade: Nome da cidade (ex.: "Goiânia", "Sorriso", "Uberaba").

    Returns:
        Dicionário com: latitude, longitude, nome_resolvido.

    Raises:
        ValueError: Cidade não encontrada na API de geocoding.
        httpx.HTTPError: Em caso de falha de rede ou HTTP não-200.
    """
    params = {
        "name": cidade,
        "count": 1,
        "language": "pt",
        "country": "BR",
    }
    with httpx.Client(timeout=_TIMEOUT) as client:
        resposta = client.get(_GEOCODING_URL, params=params)
        resposta.raise_for_status()
        dados = resposta.json()

    resultados = dados.get("results", [])
    if not resultados:
        raise ValueError(
            f"Cidade '{cidade}' não encontrada na API de geocoding Open-Meteo."
        )

    primeiro = resultados[0]
    return {
        "latitude": float(primeiro["latitude"]),
        "longitude": float(primeiro["longitude"]),
        "nome_resolvido": primeiro["name"],
    }


def buscar_previsao(cidade: str, dias: int = 5) -> dict[str, Any]:
    """Busca previsão do tempo para uma cidade brasileira.

    Resolve o nome da cidade para coordenadas e consulta a API de previsão
    do Open-Meteo. Retorna máxima, mínima, precipitação (mm) e probabilidade
    de chuva por dia.

    Args:
        cidade: Nome da cidade (ex.: "Goiânia", "Sorriso MT", "Uberaba").
        dias: Número de dias de previsão (1 a 7). Padrão: 5.

    Returns:
        Dicionário com campos:
            fonte, cidade, cidade_resolvida, dias (lista), data_consulta.
            Cada dia contém: data, temp_max_c, temp_min_c,
            precipitacao_mm, prob_chuva_pct.

    Raises:
        ValueError: Cidade não encontrada.
        httpx.HTTPError: Em caso de falha de rede ou HTTP não-200.
    """
    dias = max(1, min(dias, 7))

    coordenadas = _buscar_coordenadas(cidade)
    lat = coordenadas["latitude"]
    lon = coordenadas["longitude"]
    nome_resolvido = coordenadas["nome_resolvido"]

    params: dict[str, Any] = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        "timezone": "America/Sao_Paulo",
        "forecast_days": dias,
    }
    with httpx.Client(timeout=_TIMEOUT) as client:
        resposta = client.get(_FORECAST_URL, params=params)
        resposta.raise_for_status()
        dados_forecast = resposta.json()

    daily = dados_forecast["daily"]
    datas = daily["time"]
    temp_max = daily["temperature_2m_max"]
    temp_min = daily["temperature_2m_min"]
    precip = daily["precipitation_sum"]
    prob_chuva = daily["precipitation_probability_max"]

    previsoes = [
        {
            "data": datas[i],
            "temp_max_c": temp_max[i],
            "temp_min_c": temp_min[i],
            "precipitacao_mm": precip[i],
            "prob_chuva_pct": prob_chuva[i],
        }
        for i in range(len(datas))
    ]

    return {
        "fonte": "Open-Meteo",
        "fonte_url": "https://open-meteo.com/",
        "cidade": cidade,
        "cidade_resolvida": nome_resolvido,
        "dias": previsoes,
        "data_consulta": date.today().isoformat(),
    }
