"""Calendário de plantio e colheita das principais culturas do agronegócio brasileiro.

Dado estático curado a partir de:
  CONAB - Calendário de Plantio e Colheita de Grãos no Brasil
  https://www.conab.gov.br/info-agro/safras/calendario-de-plantio-e-colheita-de-graos-no-brasil

As janelas representam os períodos típicos; variações climáticas e de cultivar podem
deslocar o calendário em 2-4 semanas dentro da mesma região.

Culturas cobertas: soja, milho_1a, milho_2a, feijao, cafe, sorgo, algodao.
Regiões cobertas: Centro-Oeste, Sul, Sudeste, MATOPIBA, Nordeste.
"""

from __future__ import annotations

from datetime import date

# ---------------------------------------------------------------------------
# Constantes públicas (importadas pelo server e pelos testes)
# ---------------------------------------------------------------------------

CULTURAS: list[str] = [
    "soja",
    "milho_1a",
    "milho_2a",
    "feijao",
    "cafe",
    "sorgo",
    "algodao",
]

REGIOES: list[str] = [
    "Centro-Oeste",
    "Sul",
    "Sudeste",
    "MATOPIBA",
    "Nordeste",
]

# ---------------------------------------------------------------------------
# Tabela principal: cultura -> regiao -> {plantio, colheita, observacao}
# Meses como inteiros (1=jan ... 12=dez).
# ---------------------------------------------------------------------------

_CALENDARIO: dict[str, dict[str, dict[str, object]]] = {
    # -----------------------------------------------------------------------
    # SOJA
    # -----------------------------------------------------------------------
    "soja": {
        "Centro-Oeste": {
            "plantio": [10, 11, 12],
            "colheita": [1, 2, 3],
            "observacao": (
                "Maior região produtora nacional. GO, MT e MS concentram mais "
                "de 50% da produção. Plantio intensivo em out-nov; colheita "
                "em jan-mar. 1ª safra única."
            ),
        },
        "Sul": {
            "plantio": [10, 11, 12],
            "colheita": [1, 2, 3],
            "observacao": (
                "PR lidera no Sul. Plantio em out-nov; colheita em jan-mar. "
                "Em RS a colheita pode se estender até abril em algumas regiões."
            ),
        },
        "Sudeste": {
            "plantio": [10, 11],
            "colheita": [2, 3, 4],
            "observacao": (
                "MG e SP têm produção expressiva, especialmente no Triângulo Mineiro. "
                "Colheita ligeiramente mais tardia que no Centro-Oeste."
            ),
        },
        "MATOPIBA": {
            "plantio": [10, 11, 12],
            "colheita": [1, 2, 3],
            "observacao": (
                "Fronteira agrícola em expansão (MA, TO, PI, BA). Plantio em "
                "out-dez dependendo das chuvas; colheita em jan-mar."
            ),
        },
        "Nordeste": {
            "plantio": [11, 12, 1],
            "colheita": [3, 4, 5],
            "observacao": (
                "Produção menor, concentrada no oeste da BA e regiões irrigadas. "
                "Calendário ligeiramente deslocado em relação ao Centro-Oeste."
            ),
        },
    },
    # -----------------------------------------------------------------------
    # MILHO 1ª SAFRA (verão)
    # -----------------------------------------------------------------------
    "milho_1a": {
        "Centro-Oeste": {
            "plantio": [10, 11, 12, 1],
            "colheita": [3, 4, 5, 6],
            "observacao": (
                "1ª safra de verão em GO, MT e MS. Consorciada ou em sequência "
                "com a soja. Plantio out-jan; colheita mar-jun."
            ),
        },
        "Sul": {
            "plantio": [8, 9, 10, 11],
            "colheita": [1, 2, 3, 4],
            "observacao": (
                "PR e RS são grandes produtores da 1ª safra. Plantio iniciado "
                "em ago-set (mais cedo que no Centro-Oeste); colheita jan-abr."
            ),
        },
        "Sudeste": {
            "plantio": [10, 11, 12, 1],
            "colheita": [2, 3, 4, 5],
            "observacao": ("SP e MG com plantio em out-jan. Colheita concentrada em fev-mai."),
        },
        "MATOPIBA": {
            "plantio": [11, 12, 1],
            "colheita": [3, 4, 5, 6],
            "observacao": (
                "Região de expansão. 1ª safra com plantio em nov-jan; colheita em mar-jun."
            ),
        },
        "Nordeste": {
            "plantio": [12, 1, 2],
            "colheita": [4, 5, 6],
            "observacao": (
                "Produção de milho de sequeiro no semiárido e regiões úmidas. "
                "Calendário variável conforme regime de chuvas."
            ),
        },
    },
    # -----------------------------------------------------------------------
    # MILHO 2ª SAFRA (safrinha)
    # -----------------------------------------------------------------------
    "milho_2a": {
        "Centro-Oeste": {
            "plantio": [1, 2, 3],
            "colheita": [6, 7, 8],
            "observacao": (
                "Safrinha: plantada após a soja em jan-mar. MT é o maior "
                "produtor nacional de milho 2ª safra. Colheita em jun-ago."
            ),
        },
        "Sul": {
            "plantio": [1, 2],
            "colheita": [5, 6, 7],
            "observacao": (
                "PR tem safrinha expressiva, plantio jan-fev. "
                "SC e RS têm menor participação nessa janela."
            ),
        },
        "Sudeste": {
            "plantio": [1, 2],
            "colheita": [5, 6, 7],
            "observacao": (
                "MG pratica safrinha em algumas regiões. Menor expressão que no Centro-Oeste."
            ),
        },
        "MATOPIBA": {
            "plantio": [1, 2],
            "colheita": [5, 6, 7],
            "observacao": ("Safrinha crescente no MATOPIBA, plantio logo após soja em jan-fev."),
        },
        "Nordeste": {
            "plantio": [],
            "colheita": [],
            "observacao": (
                "Milho 2ª safra (safrinha) não é prática comum no Nordeste "
                "fora do MATOPIBA. Dados não cadastrados para esta região."
            ),
        },
    },
    # -----------------------------------------------------------------------
    # FEIJÃO (considere apenas 1ª e 2ª safra; a 3ª ocorre só em algumas regiões)
    # -----------------------------------------------------------------------
    "feijao": {
        "Centro-Oeste": {
            "plantio": [10, 11, 12, 1, 6, 7],
            "colheita": [1, 2, 3, 4, 9, 10],
            "observacao": (
                "GO e MT têm 2 safras principais. 1ª safra: plantio out-jan, "
                "colheita jan-abr. 3ª safra (irrigada): plantio jun-jul, "
                "colheita set-out."
            ),
        },
        "Sul": {
            "plantio": [8, 9, 10, 11, 12, 1],
            "colheita": [11, 12, 1, 2, 3, 4],
            "observacao": (
                "PR e SC têm 2 safras. 1ª safra: plantio ago-nov, colheita "
                "nov-jan. 2ª safra: plantio dez-jan, colheita fev-abr."
            ),
        },
        "Sudeste": {
            "plantio": [9, 10, 11, 1, 2, 6, 7],
            "colheita": [12, 1, 2, 3, 4, 9, 10],
            "observacao": (
                "MG e SP têm 3 safras. 1ª (das águas): set-nov/dez-jan. "
                "2ª (da seca): jan-fev/abr-mai. "
                "3ª (de inverno, irrigada): jun-jul/set-out."
            ),
        },
        "MATOPIBA": {
            "plantio": [11, 12, 1, 2],
            "colheita": [2, 3, 4, 5],
            "observacao": (
                "1ª e 2ª safras em nov-fev; colheita fev-mai. Produção concentrada na BA e TO."
            ),
        },
        "Nordeste": {
            "plantio": [12, 1, 2, 3],
            "colheita": [3, 4, 5, 6],
            "observacao": (
                "Plantio dependente das chuvas do inverno nordestino (mar-jun). "
                "Feijão de sequeiro amplamente cultivado."
            ),
        },
    },
    # -----------------------------------------------------------------------
    # CAFÉ (arábica e robusta)
    # -----------------------------------------------------------------------
    "cafe": {
        "Centro-Oeste": {
            "plantio": [10, 11, 12, 1],
            "colheita": [4, 5, 6, 7, 8, 9],
            "observacao": (
                "Cerrado Mineiro (GO/MG) e Chapada dos Veadeiros. Plantio das "
                "mudas em out-jan (início das chuvas). Colheita do café arábica "
                "em abr-set, com pico em jun-ago."
            ),
        },
        "Sul": {
            "plantio": [10, 11, 12],
            "colheita": [5, 6, 7, 8],
            "observacao": (
                "PR (Norte Pioneiro) é o maior produtor no Sul. Plantio em "
                "out-dez; colheita mai-ago."
            ),
        },
        "Sudeste": {
            "plantio": [10, 11, 12, 1],
            "colheita": [4, 5, 6, 7, 8, 9],
            "observacao": (
                "MG (sul de MG, Cerrado, Montanhas) e ES são os maiores "
                "produtores nacionais. Café arábica em MG: plantio out-jan, "
                "colheita abr-set. ES: conilon (robusta) colhido em jun-set."
            ),
        },
        "MATOPIBA": {
            "plantio": [],
            "colheita": [],
            "observacao": (
                "Cultivo de café não é representativo no MATOPIBA. "
                "Dados não cadastrados para esta região."
            ),
        },
        "Nordeste": {
            "plantio": [11, 12, 1],
            "colheita": [5, 6, 7, 8],
            "observacao": (
                "Chapada Diamantina (BA) é a principal região cafeeira do "
                "Nordeste. Café arábica de altitude."
            ),
        },
    },
    # -----------------------------------------------------------------------
    # SORGO
    # -----------------------------------------------------------------------
    "sorgo": {
        "Centro-Oeste": {
            "plantio": [1, 2, 3],
            "colheita": [5, 6, 7, 8],
            "observacao": (
                "Sorgo safrinha: plantado após soja em jan-mar, "
                "colhido em mai-ago. GO e MT são grandes produtores."
            ),
        },
        "Sul": {
            "plantio": [9, 10, 11, 12],
            "colheita": [1, 2, 3, 4],
            "observacao": (
                "Sorgo de verão: plantio set-dez, colheita jan-abr. "
                "PR tem maior participação no Sul."
            ),
        },
        "Sudeste": {
            "plantio": [10, 11, 12, 1],
            "colheita": [2, 3, 4, 5],
            "observacao": ("MG e SP com sorgo granífero em out-jan; colheita fev-mai."),
        },
        "MATOPIBA": {
            "plantio": [1, 2, 3],
            "colheita": [5, 6, 7],
            "observacao": ("Safrinha crescente: plantio jan-mar após soja, colheita mai-jul."),
        },
        "Nordeste": {
            "plantio": [12, 1, 2, 3],
            "colheita": [4, 5, 6, 7],
            "observacao": (
                "Sorgo forrageiro amplamente usado no semiárido, dependente do período chuvoso."
            ),
        },
    },
    # -----------------------------------------------------------------------
    # ALGODÃO
    # -----------------------------------------------------------------------
    "algodao": {
        "Centro-Oeste": {
            "plantio": [12, 1, 2, 3],
            "colheita": [6, 7, 8, 9, 10],
            "observacao": (
                "MT é o maior produtor nacional. Plantio de 1ª época: dez-jan; "
                "2ª época (safrinha de algodão): fev-mar. "
                "Colheita jun-out conforme a época de plantio."
            ),
        },
        "Sul": {
            "plantio": [],
            "colheita": [],
            "observacao": (
                "Cultivo de algodão não é representativo na região Sul. Dados não cadastrados."
            ),
        },
        "Sudeste": {
            "plantio": [11, 12, 1],
            "colheita": [5, 6, 7, 8],
            "observacao": (
                "SP (Alta Paulista) e MG têm produção em declínio. "
                "Plantio nov-jan; colheita mai-ago."
            ),
        },
        "MATOPIBA": {
            "plantio": [12, 1],
            "colheita": [7, 8, 9],
            "observacao": (
                "BA (Oeste) e TO são expressivos no MATOPIBA. Plantio dez-jan; colheita jul-set."
            ),
        },
        "Nordeste": {
            "plantio": [1, 2, 3],
            "colheita": [7, 8, 9, 10],
            "observacao": (
                "Algodão herbáceo de sequeiro no semiárido. Calendário dependente das chuvas."
            ),
        },
    },
}

# Mapeamento de aliases (nomes alternativos -> nome canônico)
_ALIASES_CULTURA: dict[str, str] = {
    "milho": "milho_1a",
    "milho 1a": "milho_1a",
    "milho1a": "milho_1a",
    "milho 2a": "milho_2a",
    "milho2a": "milho_2a",
    "milho safrinha": "milho_2a",
    "safrinha": "milho_2a",
    "feijão": "feijao",
    "café": "cafe",
    "algodão": "algodao",
    "soybean": "soja",
    "corn": "milho_1a",
    "cotton": "algodao",
    "coffee": "cafe",
    "sorghum": "sorgo",
    "bean": "feijao",
    "beans": "feijao",
}

_ALIASES_REGIAO: dict[str, str] = {
    "co": "Centro-Oeste",
    "centro oeste": "Centro-Oeste",
    "centro-oeste": "Centro-Oeste",
    "go": "Centro-Oeste",
    "goias": "Centro-Oeste",
    "goiás": "Centro-Oeste",
    "mt": "Centro-Oeste",
    "mato grosso": "Centro-Oeste",
    "ms": "Centro-Oeste",
    "mato grosso do sul": "Centro-Oeste",
    "sul": "Sul",
    "pr": "Sul",
    "parana": "Sul",
    "paraná": "Sul",
    "sc": "Sul",
    "santa catarina": "Sul",
    "rs": "Sul",
    "rio grande do sul": "Sul",
    "sudeste": "Sudeste",
    "se": "Sudeste",
    "sp": "Sudeste",
    "sao paulo": "Sudeste",
    "são paulo": "Sudeste",
    "mg": "Sudeste",
    "minas gerais": "Sudeste",
    "matopiba": "MATOPIBA",
    "ma": "MATOPIBA",
    "maranhao": "MATOPIBA",
    "maranhão": "MATOPIBA",
    "to": "MATOPIBA",
    "tocantins": "MATOPIBA",
    "pi": "MATOPIBA",
    "piaui": "MATOPIBA",
    "piauí": "MATOPIBA",
    "ba": "Nordeste",
    "bahia": "Nordeste",
    "nordeste": "Nordeste",
    "ne": "Nordeste",
}

_NOMES_MESES: list[str] = [
    "",  # índice 0 não usado
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
]


def _normalizar_cultura(cultura: str) -> str | None:
    """Retorna o nome canônico da cultura ou None se não reconhecido."""
    c = cultura.lower().strip()
    if c in _ALIASES_CULTURA:
        return _ALIASES_CULTURA[c]
    if c in _CALENDARIO:
        return c
    return None


def _normalizar_regiao(regiao: str) -> str | None:
    """Retorna o nome canônico da região ou None se não reconhecida."""
    r = regiao.lower().strip()
    if r in _ALIASES_REGIAO:
        return _ALIASES_REGIAO[r]
    # Tentativa case-insensitive contra nomes canônicos
    for nome in REGIOES:
        if r == nome.lower():
            return nome
    return None


def _meses_para_texto(meses: list[int]) -> str:
    """Converte lista de inteiros de mês para string legível."""
    if not meses:
        return "não cadastrado"
    return ", ".join(_NOMES_MESES[m] for m in sorted(set(meses)))


def consultar_calendario_safra(
    cultura: str,
    regiao: str | None = None,
) -> dict[str, object]:
    """Consulta o calendário de plantio e colheita de uma cultura por região.

    Fonte: CONAB - Calendário de Plantio e Colheita de Grãos no Brasil
    (https://www.conab.gov.br/info-agro/safras/calendario-de-plantio-e-colheita-de-graos-no-brasil)

    Args:
        cultura: Nome da cultura. Aceitos: soja, milho_1a, milho_2a (safrinha),
                 feijao, cafe, sorgo, algodao. Aliases comuns são reconhecidos
                 (ex.: "milho" -> milho_1a, "safrinha" -> milho_2a).
        regiao: Região produtora. Aceitas: Centro-Oeste, Sul, Sudeste, MATOPIBA,
                Nordeste. Siglas de estados são mapeadas para a região correspondente
                (ex.: "GO" -> Centro-Oeste, "PR" -> Sul). Se None, retorna todas
                as regiões cadastradas para a cultura.

    Returns:
        Dicionário com:
            cultura_consultada, cultura_normalizada, fonte, data_consulta,
            e 'regioes' (lista) ou 'resultado' (único) conforme o caso.

        Quando uma região é informada:
            resultado: {regiao, plantio_meses, colheita_meses, observacao}

        Quando nenhuma região é informada:
            regioes: [{regiao, plantio_meses, colheita_meses, observacao}, ...]

    Raises:
        ValueError: Cultura não reconhecida.
    """
    cultura_norm = _normalizar_cultura(cultura)
    if cultura_norm is None:
        culturas_disp = ", ".join(CULTURAS)
        raise ValueError(
            f"Cultura '{cultura}' não reconhecida. "
            f"Disponíveis: {culturas_disp}. "
            "Use 'milho_2a' ou 'safrinha' para o milho de 2ª safra."
        )

    dados_cultura = _CALENDARIO[cultura_norm]
    hoje = date.today().isoformat()
    fonte = (
        "CONAB - Calendário de Plantio e Colheita de Grãos no Brasil. "
        "https://www.conab.gov.br/info-agro/safras/"
        "calendario-de-plantio-e-colheita-de-graos-no-brasil"
    )

    if regiao is None:
        # Retorna todas as regiões
        regioes_resultado = [
            {
                "regiao": reg,
                "plantio_meses": _meses_para_texto(dados["plantio"]),  # type: ignore[arg-type]
                "colheita_meses": _meses_para_texto(dados["colheita"]),  # type: ignore[arg-type]
                "observacao": dados["observacao"],
            }
            for reg, dados in dados_cultura.items()
        ]
        return {
            "cultura_consultada": cultura,
            "cultura_normalizada": cultura_norm,
            "fonte": fonte,
            "data_consulta": hoje,
            "regioes": regioes_resultado,
        }

    regiao_norm = _normalizar_regiao(regiao)
    if regiao_norm is None or regiao_norm not in dados_cultura:
        regioes_disp = ", ".join(REGIOES)
        return {
            "cultura_consultada": cultura,
            "cultura_normalizada": cultura_norm,
            "regiao_consultada": regiao,
            "fonte": fonte,
            "data_consulta": hoje,
            "resultado": None,
            "aviso": (
                f"Região '{regiao}' não cadastrada para '{cultura_norm}'. "
                f"Regiões disponíveis: {regioes_disp}."
            ),
        }

    dados = dados_cultura[regiao_norm]
    return {
        "cultura_consultada": cultura,
        "cultura_normalizada": cultura_norm,
        "regiao_consultada": regiao,
        "regiao_normalizada": regiao_norm,
        "fonte": fonte,
        "data_consulta": hoje,
        "resultado": {
            "regiao": regiao_norm,
            "plantio_meses": _meses_para_texto(dados["plantio"]),  # type: ignore[arg-type]
            "colheita_meses": _meses_para_texto(dados["colheita"]),  # type: ignore[arg-type]
            "observacao": dados["observacao"],
        },
    }
