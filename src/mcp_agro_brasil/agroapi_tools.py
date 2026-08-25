"""Registro opcional das tools AgroAPI/Embrapa no servidor FastMCP."""

from __future__ import annotations

from typing import Any

from mcp_agro_brasil.providers import agroapi


def agrofit_buscar_produtos(
    termo: str = "",
    cultura: str = "",
    praga: str = "",
    ingrediente_ativo: str = "",
    categoria: str = "",
    produto_biologico: bool | None = None,
    pagina: int = 1,
) -> dict[str, Any]:
    """Busca defensivos e produtos fitossanitários registrados no AGROFIT/MAPA.

    Informe ao menos um filtro. Esta é uma consulta informativa a registros
    oficiais, não uma prescrição agronômica.

    Args:
        termo: Busca textual geral, como "mosca branca".
        cultura: Cultura agrícola, como "Soja" ou "Algodão".
        praga: Nome comum da praga ou doença.
        ingrediente_ativo: Ingrediente ativo do produto.
        categoria: Classe/categoria agronômica exata.
        produto_biologico: Filtra produtos de origem biológica quando informado.
        pagina: Página da API, começando em 1.
    """
    return agroapi.buscar_produtos_agrofit(
        termo=termo,
        cultura=cultura,
        praga=praga,
        ingrediente_ativo=ingrediente_ativo,
        categoria=categoria,
        produto_biologico=produto_biologico,
        pagina=pagina,
    )


def agrofit_consultar_produto(numero_registro: str) -> dict[str, Any]:
    """Consulta detalhes de um produto AGROFIT pelo número de registro no MAPA.

    Args:
        numero_registro: Número oficial de registro do produto formulado.
    """
    return agroapi.consultar_produto_agrofit(numero_registro)


def agritec_buscar_municipios(nome: str, uf: str) -> dict[str, Any]:
    """Resolve nome e UF de município para o código IBGE exigido pela Agritec.

    Use antes de ``agritec_consultar_zarc`` quando o código IBGE não for conhecido.

    Args:
        nome: Nome ou trecho do nome do município.
        uf: Sigla da unidade federativa, como "MT" ou "GO".
    """
    return agroapi.buscar_municipios_agritec(nome, uf)


def agritec_buscar_culturas(nome: str) -> dict[str, Any]:
    """Resolve nome de cultura para o identificador exigido pela Agritec.

    Use antes das consultas de ZARC ou cultivares quando o ID não for conhecido.

    Args:
        nome: Nome ou trecho do nome da cultura, como "soja" ou "milho".
    """
    return agroapi.buscar_culturas_agritec(nome)


def agritec_consultar_zarc(
    codigo_ibge: int,
    id_cultura: int,
    risco: str = "todos",
) -> dict[str, Any]:
    """Consulta o Zoneamento Agrícola de Risco Climático oficial na Agritec.

    Args:
        codigo_ibge: Código IBGE do município; resolva com agritec_buscar_municipios.
        id_cultura: ID da cultura; resolva com agritec_buscar_culturas.
        risco: Nível de risco: "20", "30", "40" ou "todos".
    """
    return agroapi.consultar_zarc_agritec(codigo_ibge, id_cultura, risco)


def agritec_buscar_cultivares(
    id_cultura: int,
    uf: str,
    safra: str = "2026-2027",
    regiao: str = "",
    grupo: str = "",
    cultivar: str = "",
) -> dict[str, Any]:
    """Busca cultivares indicadas pela Agritec para cultura, UF e safra.

    Args:
        id_cultura: ID da cultura; resolva com agritec_buscar_culturas.
        uf: Sigla da unidade federativa.
        safra: Safra no formato YYYY-YYYY. Padrão: "2026-2027".
        regiao: Região Agritec opcional, de "1" a "5".
        grupo: Grupo opcional: I, II, III ou IV.
        cultivar: Trecho opcional do nome da cultivar.
    """
    return agroapi.buscar_cultivares_agritec(
        id_cultura=id_cultura,
        uf=uf,
        safra=safra,
        regiao=regiao,
        grupo=grupo,
        cultivar=cultivar,
    )


def bioinsumos_buscar_produtos(
    tipo: str = "biologico",
    termo: str = "",
    cultura: str = "",
    praga: str = "",
    ingrediente_ativo: str = "",
    uf: str = "",
    especie: str = "",
    pagina: int = 1,
) -> dict[str, Any]:
    """Busca produtos biológicos ou inoculantes registrados no MAPA.

    Informe ao menos um filtro. Para ``tipo="biologico"``, use praga e
    ingrediente_ativo. Para ``tipo="inoculante"``, use UF e espécie.

    Args:
        tipo: "biologico" ou "inoculante".
        termo: Busca textual geral.
        cultura: Cultura agrícola.
        praga: Nome comum da praga; exclusivo de produtos biológicos.
        ingrediente_ativo: Ingrediente; exclusivo de produtos biológicos.
        uf: UF do titular; exclusiva de inoculantes.
        especie: Espécie do microrganismo; exclusiva de inoculantes.
        pagina: Página da API, começando em 1.
    """
    return agroapi.buscar_produtos_bioinsumos(
        tipo=tipo,
        termo=termo,
        cultura=cultura,
        praga=praga,
        ingrediente_ativo=ingrediente_ativo,
        uf=uf,
        especie=especie,
        pagina=pagina,
    )


def agrotermos_buscar(termo: str, incluir_relacoes: bool = False) -> dict[str, Any]:
    """Busca termos, conceitos e relações no vocabulário AgroTermos da Embrapa.

    A busca comum aceita fragmentos. Para incluir relações semânticas, informe
    o nome completo e exato do termo ou conceito.

    Args:
        termo: Fragmento; ou termo exato quando incluir_relacoes for verdadeiro.
        incluir_relacoes: Consulta relações de um termo exato quando verdadeiro.
    """
    return agroapi.buscar_termos_agrotermos(termo, incluir_relacoes)


_TOOLS = (
    agrofit_buscar_produtos,
    agrofit_consultar_produto,
    agritec_buscar_municipios,
    agritec_buscar_culturas,
    agritec_consultar_zarc,
    agritec_buscar_cultivares,
    bioinsumos_buscar_produtos,
    agrotermos_buscar,
)


def registrar_tools_agroapi(app: Any, *, enabled: bool | None = None) -> bool:
    """Registra o bloco AgroAPI somente quando há configuração completa."""
    should_enable = agroapi.is_configured() if enabled is None else enabled
    if not should_enable:
        return False
    for tool in _TOOLS:
        app.tool(tool)
    return True
