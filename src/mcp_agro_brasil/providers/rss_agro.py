"""Provider de notícias do agronegócio via RSS.

Fonte: Canal Rural (https://www.canalrural.com.br/feed)
Feed RSS 2.0 público, sem autenticação. Atualizado várias vezes ao dia.

Parsing com defusedxml (seguro contra XXE e billion-laughs), não com stdlib ET.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any
from xml.etree.ElementTree import Element

import defusedxml.ElementTree as ET  # type: ignore[import-untyped]  # noqa: N817
import httpx

_FEEDS: list[dict[str, str]] = [
    {
        "nome": "Canal Rural",
        "url": "https://www.canalrural.com.br/feed",
    },
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

_TIMEOUT = 15.0

# Namespace dc (Dublin Core) usado para <dc:creator>
_NS_DC = "http://purl.org/dc/elements/1.1/"


def _texto(elem: Element | None) -> str:
    """Extrai texto de um elemento XML, retornando string vazia se None."""
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def _parsear_itens(xml_texto: str, fonte: str) -> list[dict[str, str]]:
    """Extrai itens de um feed RSS 2.0.

    Args:
        xml_texto: Conteúdo XML do feed.
        fonte: Nome da fonte (ex: "Canal Rural").

    Returns:
        Lista de dicionários com campos: titulo, link, data, descricao, fonte.
    """
    root = ET.fromstring(xml_texto)
    canal = root.find("channel")
    if canal is None:
        return []

    itens: list[dict[str, str]] = []
    for item in canal.findall("item"):
        titulo = _texto(item.find("title"))
        link = _texto(item.find("link"))
        pub_date = _texto(item.find("pubDate"))
        descricao_elem = item.find("description")
        descricao = ""
        if descricao_elem is not None and descricao_elem.text:
            # Remove tags HTML da descrição via regex simples
            descricao = re.sub(r"<[^>]+>", "", descricao_elem.text).strip()

        if titulo and link:
            itens.append(
                {
                    "titulo": titulo,
                    "link": link,
                    "data": pub_date,
                    "descricao": descricao[:200] if descricao else "",
                    "fonte": fonte,
                }
            )

    return itens


def buscar_noticias(tema: str | None = None, limite: int = 5) -> dict[str, Any]:
    """Busca as últimas notícias do agronegócio via RSS.

    Consolida feeds configurados. Se `tema` for fornecido, filtra itens
    cujo título contenha a palavra-chave (case-insensitive).

    Args:
        tema: Palavra-chave para filtrar títulos (ex: "soja", "boi gordo").
              None para retornar as mais recentes sem filtro.
        limite: Número máximo de notícias a retornar (padrão: 5, máximo: 20).

    Returns:
        Dicionário com campos:
            fonte, feeds_consultados, tema_filtro, total, noticias (lista),
            data_consulta.
            Cada notícia contém: titulo, link, data, descricao, fonte.

    Raises:
        RuntimeError: Se todos os feeds falharem.
    """
    limite = max(1, min(limite, 20))
    tema_lower = tema.lower().strip() if tema else None

    todas_noticias: list[dict[str, str]] = []
    feeds_ok: list[str] = []
    erros: list[str] = []

    for feed in _FEEDS:
        try:
            with httpx.Client(
                headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True
            ) as client:
                resp = client.get(feed["url"])
                resp.raise_for_status()
                itens = _parsear_itens(resp.text, feed["nome"])
                todas_noticias.extend(itens)
                feeds_ok.append(feed["nome"])
        except Exception as exc:
            erros.append(f"{feed['nome']}: {exc}")

    if not feeds_ok:
        raise RuntimeError(
            f"Todos os feeds de notícias falharam. Erros: {'; '.join(erros)}"
        )

    # Filtra por tema se fornecido
    if tema_lower:
        filtradas = [n for n in todas_noticias if tema_lower in n["titulo"].lower()]
    else:
        filtradas = todas_noticias

    resultado = filtradas[:limite]

    return {
        "fonte": "Canal Rural",
        "feeds_consultados": feeds_ok,
        "tema_filtro": tema,
        "total": len(resultado),
        "noticias": resultado,
        "data_consulta": date.today().isoformat(),
    }
