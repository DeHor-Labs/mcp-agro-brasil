"""Servidor MCP Agro Brasil.

Registra tools no FastMCP e expõe via stdio (padrão) ou HTTP streamable.

Tools expostas:
- cotacao_boi_gordo     : cotação regional de boi gordo (Scot, fallback ESALQ)
- indicador_esalq       : indicador nacional ESALQ/B3 de boi gordo
- converter             : conversões de unidades do agronegócio (peso e área)
- listar_pracas         : praças disponíveis no provider Scot
- listar_unidades       : unidades suportadas pelo módulo de conversão
"""

from __future__ import annotations

import fastmcp

from mcp_agro_brasil.core import conversao, cotacao

app = fastmcp.FastMCP(
    name="MCP Agro Brasil",
    version="0.1.0",
    instructions=(
        "Ferramentas de dados do agronegócio brasileiro. "
        "Cotações de boi gordo via Scot Consultoria (regional) e ESALQ/B3 (nacional). "
        "Conversões de unidades: arroba, saca, hectare, alqueire e mais. "
        "AVISO: cotações são scrapeadas de fontes públicas e podem ter defasagem de "
        "minutos a horas em relação ao mercado em tempo real. "
        "Roadmap: soja, milho, café, leite, câmbio, safra, notícias."
    ),
)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@app.tool()
def cotacao_boi_gordo(praca: str = "GO Goiânia") -> dict[str, object]:
    """Retorna a cotação de boi gordo para uma praça regional brasileira.

    Fonte primária: Scot Consultoria (tabela regional).
    Fallback: indicador nacional ESALQ/B3 se a praça não for encontrada.

    Args:
        praca: Nome da praça (ex.: "GO Goiânia", "MS Campo Grande"). Padrão: "GO Goiânia".

    Returns:
        Cotação com campos: praca, a_vista (R$/@), trinta_dias (R$/@),
        unidade, moeda, fonte, data_consulta, fallback, cache_hit.
    """
    return cotacao.cotacao_boi_gordo(praca)


@app.tool()
def indicador_esalq() -> dict[str, object]:
    """Retorna o indicador nacional ESALQ/B3 de boi gordo.

    Referência amplamente utilizada como benchmark nacional de preço.
    Fonte: Notícias Agrícolas / ESALQ-USP / B3.

    Returns:
        Dicionário com: indicador, a_vista (R$/@), unidade, moeda, fonte, data_consulta.
    """
    return cotacao.indicador_esalq()


@app.tool()
def converter(valor: float, de_unidade: str, para_unidade: str) -> dict[str, object]:
    """Converte valor entre unidades do agronegócio (peso ou área).

    Unidades de peso: kg, g, t, @ (arroba), arroba, saca, saca_soja,
      saca_milho, saca_cafe, saca_cafe_verde, lb.
    Unidades de área: m2, ha, hectare, km2, alqueire_goiano,
      alqueire_paulista, alqueire_mineiro, alqueire, acre.

    Args:
        valor: Quantidade na unidade de origem.
        de_unidade: Unidade de origem (case-insensitive, ex.: "arroba", "ha").
        para_unidade: Unidade de destino.

    Returns:
        Dicionário com: valor_original, de_unidade, resultado, para_unidade.

    Raises:
        ValueError: Unidade desconhecida ou conversão entre categorias diferentes.
    """
    resultado = conversao.converter(valor, de_unidade, para_unidade)
    return {
        "valor_original": valor,
        "de_unidade": de_unidade,
        "resultado": resultado,
        "para_unidade": para_unidade,
    }


@app.tool()
def listar_pracas() -> dict[str, object]:
    """Lista as praças disponíveis para cotação de boi gordo via Scot Consultoria.

    Returns:
        Dicionário com: pracas (lista), total, provider, nota.
    """
    return {
        "pracas": cotacao.PRACAS_SCOT,
        "total": len(cotacao.PRACAS_SCOT),
        "provider": "Scot Consultoria",
        "nota": (
            "Para praças fora desta lista, o sistema usa fallback "
            "para o indicador nacional ESALQ/B3."
        ),
    }


@app.tool()
def listar_unidades() -> dict[str, object]:
    """Lista todas as unidades suportadas pelo conversor de unidades.

    Returns:
        Dicionário com: unidades_peso (lista) e unidades_area (lista).
    """
    return {
        "unidades_peso": conversao.UNIDADES_PESO,
        "unidades_area": conversao.UNIDADES_AREA,
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """Ponto de entrada para execução via CLI."""
    app.run()


if __name__ == "__main__":
    main()
