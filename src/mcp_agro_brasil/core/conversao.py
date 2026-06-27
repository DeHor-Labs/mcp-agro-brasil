"""Conversões de unidades do agronegócio brasileiro.

Cálculos puramente matemáticos, sem rede.
Referências:
  - Arroba (@) boi gordo: 15 kg
  - Saca de grãos (soja, milho, trigo): 60 kg
  - Saca de café: 60 kg (beneficiado) / 48 kg (verde)
  - Hectare (ha): 10.000 m²
  - Alqueire goiano: 48.400 m²  (4,84 ha)
  - Alqueire paulista: 24.200 m²  (2,42 ha)
  - Alqueire mineiro: 48.400 m²  (equivale ao goiano)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Tabela de conversão: unidade -> kg
# Usamos kg como unidade canônica intermediária para conversões de peso.
# Para área, usamos m² como unidade canônica.
# ---------------------------------------------------------------------------

_KG_POR_UNIDADE: dict[str, float] = {
    # Peso
    "kg": 1.0,
    "g": 0.001,
    "t": 1_000.0,
    "tonelada": 1_000.0,
    # Arroba
    "@": 15.0,
    "arroba": 15.0,
    "arroba_boi": 15.0,  # alias explícito
    # Sacas
    "saca": 60.0,
    "saca_soja": 60.0,
    "saca_milho": 60.0,
    "saca_trigo": 60.0,
    "saca_cafe": 60.0,
    "saca_cafe_verde": 48.0,
    # Libra
    "lb": 0.453592,
    "libra": 0.453592,
}

_M2_POR_UNIDADE: dict[str, float] = {
    # Área
    "m2": 1.0,
    "ha": 10_000.0,
    "hectare": 10_000.0,
    "km2": 1_000_000.0,
    "alqueire_goiano": 48_400.0,
    "alqueire_paulista": 24_200.0,
    "alqueire_mineiro": 48_400.0,
    "alqueire": 48_400.0,  # padrão goiano/mineiro
    "acre": 4_046.856,
}

# Unidades suportadas (expostas para listar_unidades)
UNIDADES_PESO = sorted(_KG_POR_UNIDADE.keys())
UNIDADES_AREA = sorted(_M2_POR_UNIDADE.keys())


def _normalizar(unidade: str) -> str:
    """Normaliza: minúsculo, sem espaços, troca espaço/hífen por underscore."""
    return unidade.strip().lower().replace(" ", "_").replace("-", "_")


def converter(valor: float, de: str, para: str) -> float:
    """Converte `valor` da unidade `de` para `para`.

    Suporta unidades de peso (kg, arroba, saca, ...) e área (ha, alqueire, ...).
    Conversões cruzadas (peso <-> área) não são suportadas e levantam ValueError.

    Args:
        valor: Quantidade na unidade de origem.
        de: Unidade de origem (case-insensitive, ex.: "arroba", "@", "ha").
        para: Unidade de destino.

    Returns:
        Valor convertido como float.

    Raises:
        ValueError: Unidade desconhecida ou conversão entre categorias distintas.

    Exemplos:
        >>> converter(1.0, "@", "kg")
        15.0
        >>> converter(60.0, "kg", "saca")
        1.0
        >>> converter(1.0, "ha", "alqueire_goiano")
        0.20661157024793386
    """
    de_norm = _normalizar(de)
    para_norm = _normalizar(para)

    # Determina categoria de cada unidade
    de_peso = de_norm in _KG_POR_UNIDADE
    para_peso = para_norm in _KG_POR_UNIDADE
    de_area = de_norm in _M2_POR_UNIDADE
    para_area = para_norm in _M2_POR_UNIDADE

    if not (de_peso or de_area):
        raise ValueError(
            f"Unidade de origem desconhecida: '{de}'. "
            f"Pesos suportados: {UNIDADES_PESO}. Áreas: {UNIDADES_AREA}."
        )
    if not (para_peso or para_area):
        raise ValueError(
            f"Unidade de destino desconhecida: '{para}'. "
            f"Pesos suportados: {UNIDADES_PESO}. Áreas: {UNIDADES_AREA}."
        )
    if de_peso and para_area or de_area and para_peso:
        raise ValueError(
            f"Conversão cruzada não suportada: '{de}' (peso) <-> '{para}' (área)."
        )

    if de_peso:
        # Converte via kg como intermediário
        em_kg = valor * _KG_POR_UNIDADE[de_norm]
        return em_kg / _KG_POR_UNIDADE[para_norm]
    else:
        # Converte via m² como intermediário
        em_m2 = valor * _M2_POR_UNIDADE[de_norm]
        return em_m2 / _M2_POR_UNIDADE[para_norm]
