"""Testes dos providers Scot e ESALQ usando HTML de fixture (sem rede)."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_agro_brasil.providers.esalq import (
    _PADRAO_A_VISTA,
    _parse_valor,
    buscar_indicador_esalq,
)
from mcp_agro_brasil.providers.scot import _extrair_cotacao_praca, buscar_cotacao_boi

FIXTURES = Path(__file__).parent / "fixtures"


def _html_scot() -> str:
    return (FIXTURES / "scot_boi_gordo.html").read_text(encoding="utf-8")


def _html_esalq() -> str:
    return (FIXTURES / "esalq_boi_gordo.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Testes Scot
# ---------------------------------------------------------------------------


class TestScotParsing:
    def test_extrai_go_goiania(self) -> None:
        resultado = _extrair_cotacao_praca(_html_scot(), "GO Goiânia")
        assert resultado["a_vista"] == pytest.approx(316.50)
        assert resultado["trinta_dias"] == pytest.approx(318.00)

    def test_extrai_ms_campo_grande(self) -> None:
        resultado = _extrair_cotacao_praca(_html_scot(), "MS Campo Grande")
        assert resultado["a_vista"] == pytest.approx(314.00)
        assert resultado["trinta_dias"] == pytest.approx(315.50)

    def test_extrai_sp_aracatuba(self) -> None:
        resultado = _extrair_cotacao_praca(_html_scot(), "SP Araçatuba")
        assert resultado["a_vista"] == pytest.approx(320.00)

    def test_praca_inexistente_retorna_none(self) -> None:
        resultado = _extrair_cotacao_praca(_html_scot(), "XX Inexistente")
        assert resultado["a_vista"] is None
        assert resultado["trinta_dias"] is None

    def test_parse_valor_virgula(self) -> None:
        assert _parse_valor("316,50") == pytest.approx(316.50)

    def test_parse_valor_ponto_milhar(self) -> None:
        assert _parse_valor("1.316,50") == pytest.approx(1316.50)

    def test_parse_valor_inteiro(self) -> None:
        assert _parse_valor("316") == pytest.approx(316.0)


class TestScotBusca:
    def test_buscar_cotacao_retorna_campos_obrigatorios(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Testa que buscar_cotacao_boi retorna estrutura correta (HTTP mockado)."""
        import httpx

        class MockResponse:
            text = _html_scot()
            status_code = 200

            def raise_for_status(self) -> None:
                pass

        class MockClient:
            def __enter__(self) -> "MockClient":
                return self

            def __exit__(self, *args: object) -> None:
                pass

            def get(self, url: str) -> MockResponse:
                return MockResponse()

        monkeypatch.setattr(httpx, "Client", lambda **kw: MockClient())

        resultado = buscar_cotacao_boi("GO Goiânia")
        assert resultado["a_vista"] == pytest.approx(316.50)
        assert resultado["moeda"] == "BRL"
        assert resultado["unidade"] == "@"
        assert resultado["fonte"] == "Scot Consultoria"
        assert resultado["praca"] == "GO Goiânia"


# ---------------------------------------------------------------------------
# Testes ESALQ
# ---------------------------------------------------------------------------


class TestEsalqParsing:
    def test_extrai_a_vista(self) -> None:
        html = _html_esalq()
        match = _PADRAO_A_VISTA.search(html)
        assert match is not None
        assert _parse_valor(match.group(1)) == pytest.approx(338.65)

    def test_padrao_sem_match_retorna_none(self) -> None:
        match = _PADRAO_A_VISTA.search("<html>sem cotacao aqui</html>")
        assert match is None


class TestEsalqBusca:
    def test_buscar_indicador_retorna_campos_obrigatorios(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import httpx

        class MockResponse:
            text = _html_esalq()
            status_code = 200

            def raise_for_status(self) -> None:
                pass

        class MockClient:
            def __enter__(self) -> "MockClient":
                return self

            def __exit__(self, *args: object) -> None:
                pass

            def get(self, url: str) -> MockResponse:
                return MockResponse()

        monkeypatch.setattr(httpx, "Client", lambda **kw: MockClient())

        resultado = buscar_indicador_esalq()
        assert resultado["a_vista"] == pytest.approx(338.65)
        assert resultado["moeda"] == "BRL"
        assert resultado["unidade"] == "@"
        assert "ESALQ" in resultado["fonte"]
