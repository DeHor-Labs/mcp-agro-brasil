"""Dump de cotações em JSON para consumo por cron externo (ex.: agrovoz).

Uso:
    python -m mcp_agro_brasil.dump --produtos boi_gordo,soja,milho,leite --leite-estados GO

Imprime no stdout um único JSON com o contrato fixo:
    {"gerado_em": <ISO 8601 com timezone>, "itens": [...], "erros": [...]}

Sucesso parcial: produto cujo provider falhou entra em "erros" com motivo;
os demais saem normalmente em "itens". Exit code 0 se pelo menos um produto
teve sucesso, 1 se todos falharam. Nenhuma chamada de rede acontece no import.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from mcp_agro_brasil.core import cotacao

PRODUTOS_SUPORTADOS: tuple[str, ...] = ("boi_gordo", "soja", "milho", "leite")

PRACA_BOI_GOIANIA = "GO Goiânia"

# Mapeia marcadores encontrados na string de fonte dos providers para as
# fontes canônicas que o consumidor (voice-brain do agrovoz) já grava hoje.
# A ordem importa: "ESALQ/B3" precisa vencer antes do marcador genérico "esalq".
_FONTES_CANONICAS: tuple[tuple[str, str], ...] = (
    ("scot", "Scot Consultoria"),
    ("esalq/b3", "ESALQ/B3"),
    ("cepea", "CEPEA"),
    ("esalq", "ESALQ/B3"),
)

# Unidades dos providers -> unidades do contrato.
_UNIDADES_CANONICAS: dict[str, str] = {
    "@": "@",
    "saca": "saca 60kg",
    "L": "litro",
}


def normalizar_fonte(fonte: str) -> str:
    """Normaliza a fonte do provider para uma das strings canônicas do contrato.

    Fonte sem marcador conhecido é devolvida como veio (nunca inventar).
    """
    baixo = fonte.lower()
    for marcador, canonica in _FONTES_CANONICAS:
        if marcador in baixo:
            return canonica
    return fonte


def _item(
    produto: str,
    dados: dict[str, Any],
    nivel: str,
    uf: str | None = None,
    localidade: str | None = None,
) -> dict[str, Any]:
    """Converte o dicionário do core para um item do contrato de dump."""
    unidade = str(dados["unidade"])
    return {
        "produto": produto,
        "valor": float(dados["a_vista"]),
        "unidade": _UNIDADES_CANONICAS.get(unidade, unidade),
        "fonte": normalizar_fonte(str(dados["fonte"])),
        "data": str(dados["data_consulta"]),
        "nivel": nivel,
        "uf": uf,
        "localidade": localidade,
    }


def _coletar_boi_gordo() -> tuple[list[dict[str, Any]], list[str]]:
    """Coleta boi gordo: indicador nacional ESALQ/B3 e, se houver, praça Goiânia."""
    itens: list[dict[str, Any]] = []
    motivos: list[str] = []

    try:
        nacional = cotacao.indicador_esalq()
        if nacional.get("a_vista") is not None:
            itens.append(_item("boi_gordo", nacional, "br"))
        else:
            motivos.append("nacional: valor à vista não encontrado (ESALQ)")
    except Exception as exc:
        motivos.append(f"nacional: {exc}")

    try:
        goiania = cotacao.cotacao_boi_gordo(PRACA_BOI_GOIANIA)
        # fallback=True significa que a Scot não respondeu e o valor já é o
        # nacional ESALQ, coberto pelo item acima. Não duplicar.
        if not goiania.get("fallback") and goiania.get("a_vista") is not None:
            itens.append(_item("boi_gordo", goiania, "municipio", uf="GO", localidade="GOIANIA"))
    except Exception as exc:
        motivos.append(f"praça Goiânia: {exc}")

    return itens, motivos


def _coletar_indicador_br(
    produto: str, buscar: Callable[[], dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Coleta um produto de indicador nacional único (soja, milho)."""
    try:
        dados = buscar()
    except Exception as exc:
        return [], [str(exc)]
    if dados.get("a_vista") is None:
        return [], ["valor à vista não encontrado"]
    return [_item(produto, dados, "br")], []


def _coletar_leite(estados: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    """Coleta leite: um item por estado pedido (nivel uf) + média Brasil (nivel br)."""
    itens: list[dict[str, Any]] = []
    motivos: list[str] = []

    for estado in estados:
        try:
            dados = cotacao.cotacao_leite(estado)
            if dados.get("a_vista") is not None:
                itens.append(_item("leite", dados, "uf", uf=estado))
            else:
                motivos.append(f"{estado}: estado não encontrado na tabela CEPEA")
        except Exception as exc:
            motivos.append(f"{estado}: {exc}")

    try:
        brasil = cotacao.cotacao_leite("Brasil")
        if brasil.get("a_vista") is not None:
            itens.append(_item("leite", brasil, "br"))
        else:
            motivos.append("Brasil: média nacional não encontrada na tabela CEPEA")
    except Exception as exc:
        motivos.append(f"Brasil: {exc}")

    return itens, motivos


def _coletar_produto(
    produto: str, leite_estados: list[str]
) -> tuple[list[dict[str, Any]], list[str]]:
    if produto == "boi_gordo":
        return _coletar_boi_gordo()
    if produto == "soja":
        return _coletar_indicador_br("soja", cotacao.cotacao_soja)
    if produto == "milho":
        return _coletar_indicador_br("milho", cotacao.cotacao_milho)
    if produto == "leite":
        return _coletar_leite(leite_estados)
    return [], [f"produto desconhecido (aceitos: {', '.join(PRODUTOS_SUPORTADOS)})"]


def main(argv: list[str] | None = None) -> int:
    """Executa o dump e imprime o JSON no stdout. Retorna o exit code."""
    parser = argparse.ArgumentParser(
        prog="python -m mcp_agro_brasil.dump",
        description="Emite cotações agro em JSON para consumo por cron externo.",
    )
    parser.add_argument(
        "--produtos",
        default=",".join(PRODUTOS_SUPORTADOS),
        help="Lista separada por vírgula (padrão: todos os suportados).",
    )
    parser.add_argument(
        "--leite-estados",
        default="",
        help="UFs para o leite, separadas por vírgula (ex.: GO,MG). Média Brasil sempre incluída.",
    )
    args = parser.parse_args(argv)

    produtos = [p.strip() for p in args.produtos.split(",") if p.strip()]
    leite_estados = [e.strip().upper() for e in args.leite_estados.split(",") if e.strip()]

    itens: list[dict[str, Any]] = []
    erros: list[dict[str, str]] = []
    produtos_com_sucesso = 0

    for produto in produtos:
        novos, motivos = _coletar_produto(produto, leite_estados)
        itens.extend(novos)
        if novos:
            produtos_com_sucesso += 1
        if motivos:
            erros.append({"produto": produto, "motivo": "; ".join(motivos)})
        elif not novos:
            erros.append({"produto": produto, "motivo": "sem dados"})

    payload = {
        "gerado_em": datetime.now(UTC).isoformat(),
        "itens": itens,
        "erros": erros,
    }
    print(json.dumps(payload, ensure_ascii=False))

    return 0 if produtos_com_sucesso > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
