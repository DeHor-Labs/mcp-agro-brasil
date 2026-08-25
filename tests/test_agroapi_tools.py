"""Testes do registro condicional das tools AgroAPI."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from mcp_agro_brasil.agroapi_tools import registrar_tools_agroapi

_AGROAPI_ENV_NAMES = (
    "AGROAPI_TOKEN",
    "AGROAPI_ACCESS_TOKEN",
    "AGROAPI_CLIENT_ID",
    "AGROAPI_CONSUMER_KEY",
    "AGROAPI_CLIENT_SECRET",
    "AGROAPI_CONSUMER_SECRET",
)
_EXPECTED_TOOLS = [
    "agrofit_buscar_produtos",
    "agrofit_consultar_produto",
    "agritec_buscar_municipios",
    "agritec_buscar_culturas",
    "agritec_consultar_zarc",
    "agritec_buscar_cultivares",
    "bioinsumos_buscar_produtos",
    "agrotermos_buscar",
]


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
    assert app.tools == _EXPECTED_TOOLS


def test_decisao_automatica_sem_configuracao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for nome in _AGROAPI_ENV_NAMES:
        monkeypatch.delenv(nome, raising=False)
    app = FakeApp()

    assert registrar_tools_agroapi(app) is False
    assert app.tools == []


def test_decisao_automatica_com_credenciais_oauth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for nome in _AGROAPI_ENV_NAMES:
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setenv("AGROAPI_CLIENT_ID", "cliente")
    monkeypatch.setenv("AGROAPI_CLIENT_SECRET", "segredo")
    app = FakeApp()

    assert registrar_tools_agroapi(app) is True
    assert app.tools == _EXPECTED_TOOLS
