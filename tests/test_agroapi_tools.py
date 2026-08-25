"""Testes do registro condicional das tools AgroAPI."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp_agro_brasil.agroapi_tools import registrar_tools_agroapi


class FakeApp:
    def __init__(self) -> None:
        self.tools: list[str] = []

    def tool(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        self.tools.append(fn.__name__)
        return fn


def test_sem_configuracao_nao_registra_tools() -> None:
    app = FakeApp()
    assert registrar_tools_agroapi(app, enabled=False) is False
    assert app.tools == []


def test_com_configuracao_registra_primeira_onda_completa() -> None:
    app = FakeApp()
    assert registrar_tools_agroapi(app, enabled=True) is True
    assert app.tools == [
        "agrofit_buscar_produtos",
        "agrofit_consultar_produto",
        "agritec_buscar_municipios",
        "agritec_buscar_culturas",
        "agritec_consultar_zarc",
        "agritec_buscar_cultivares",
        "bioinsumos_buscar_produtos",
        "agrotermos_buscar",
    ]
