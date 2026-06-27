"""Servidor MCP Agro Brasil.

Registra tools no FastMCP e expõe via stdio (padrão) ou HTTP streamable.

Tools expostas:
- cotacao_boi_gordo     : cotação regional de boi gordo (Scot, fallback ESALQ)
- indicador_esalq       : indicador nacional ESALQ/B3 de boi gordo
- cotacao_soja          : indicador CEPEA/ESALQ de soja - Porto de Paranaguá
- cotacao_milho         : indicador CEPEA/ESALQ de milho
- cotacao_leite         : preço ao produtor CEPEA de leite por estado
- clima_previsao        : previsão do tempo para cidade brasileira (Open-Meteo)
- cambio_dolar          : cotação PTAX oficial USD/BRL (Banco Central do Brasil)
- converter             : conversões de unidades do agronegócio (peso e área)
- listar_pracas         : praças disponíveis no provider Scot
- listar_produtos       : produtos com cotação disponível
- listar_unidades       : unidades suportadas pelo módulo de conversão
"""

from __future__ import annotations

import fastmcp

from mcp_agro_brasil.core import conversao, cotacao

app = fastmcp.FastMCP(
    name="MCP Agro Brasil",
    version="0.2.0",
    instructions=(
        "Ferramentas de dados do agronegócio brasileiro. "
        "Cotações de boi gordo via Scot Consultoria (regional) e ESALQ/B3 (nacional). "
        "Cotações de grãos: soja e milho via indicadores CEPEA/ESALQ; leite ao produtor CEPEA por estado. "
        "Previsão do tempo para cidades brasileiras via Open-Meteo (máxima, mínima, chuva). "
        "Câmbio dólar PTAX oficial via Banco Central do Brasil. "
        "Conversões de unidades: arroba, saca, hectare, alqueire e mais. "
        "AVISO: cotações são scrapeadas de fontes públicas e podem ter defasagem de "
        "minutos a horas em relação ao mercado em tempo real."
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
def cotacao_soja() -> dict[str, object]:
    """Retorna o indicador CEPEA/ESALQ de soja - Porto de Paranaguá.

    Referência nacional amplamente utilizada como benchmark de preço da soja.
    Fonte: Notícias Agrícolas / CEPEA-ESALQ.

    Returns:
        Dicionário com: indicador, a_vista (R$/saca 60 kg), unidade, moeda,
        fonte, data_consulta, cache_hit.
    """
    return cotacao.cotacao_soja()


@app.tool()
def cotacao_milho() -> dict[str, object]:
    """Retorna o indicador CEPEA/ESALQ de milho.

    Referência nacional de preço do milho.
    Fonte: Notícias Agrícolas / CEPEA-ESALQ.

    Returns:
        Dicionário com: indicador, a_vista (R$/saca 60 kg), unidade, moeda,
        fonte, data_consulta, cache_hit.
    """
    return cotacao.cotacao_milho()


@app.tool()
def cotacao_leite(estado: str = "Brasil") -> dict[str, object]:
    """Retorna o preço ao produtor de leite (CEPEA) por estado.

    Fonte: Notícias Agrícolas / CEPEA.
    Estados disponíveis: RS, SC, PR, SP, MG, GO, BA, RJ, ES, Brasil (média nacional).

    Args:
        estado: Sigla do estado (ex.: 'GO', 'MG', 'SP') ou 'Brasil'. Padrão: 'Brasil'.

    Returns:
        Dicionário com: indicador, estado, a_vista (R$/litro), unidade, moeda,
        fonte, data_consulta, cache_hit.
    """
    return cotacao.cotacao_leite(estado)


@app.tool()
def clima_previsao(cidade: str, dias: int = 5) -> dict[str, object]:
    """Retorna a previsão do tempo para uma cidade brasileira.

    Fonte: Open-Meteo (https://open-meteo.com/). API aberta, sem token.
    Resolve o nome da cidade por geocoding antes de buscar a previsão.

    Args:
        cidade: Nome da cidade (ex.: "Goiânia", "Sorriso MT", "Uberaba").
        dias: Número de dias de previsão, de 1 a 7. Padrão: 5.

    Returns:
        Dicionário com: fonte, cidade, cidade_resolvida, data_consulta,
        dias (lista). Cada dia contém: data, temp_max_c, temp_min_c,
        precipitacao_mm, prob_chuva_pct.
    """
    return cotacao.clima_previsao(cidade, dias)


@app.tool()
def cambio_dolar() -> dict[str, object]:
    """Retorna a cotação PTAX oficial do dólar americano (USD/BRL).

    Fonte: Banco Central do Brasil (API Olinda/PTAX).
    PTAX é a taxa de câmbio de referência oficial para contratos e conversões
    tributárias. Em fins de semana e feriados, retorna o último dia útil.

    Returns:
        Dicionário com: fonte, moeda_origem (USD), moeda_destino (BRL),
        compra, venda, data_hora_cotacao, data_consulta, cache_hit.
    """
    return cotacao.cambio_dolar()


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
def listar_produtos() -> dict[str, object]:
    """Lista todos os produtos com cotação disponível no MCP Agro Brasil.

    Returns:
        Dicionário com: produtos (lista), total, nota.
    """
    return {
        "produtos": cotacao.PRODUTOS_DISPONIVEIS,
        "total": len(cotacao.PRODUTOS_DISPONIVEIS),
        "nota": (
            "Para grãos use cotacao_soja, cotacao_milho ou cotacao_leite. "
            "Para boi gordo use cotacao_boi_gordo ou indicador_esalq. "
            "Para clima use clima_previsao. Para câmbio use cambio_dolar."
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
