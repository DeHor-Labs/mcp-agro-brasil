"""Testes dos providers de grãos (soja, milho, leite) usando HTML de fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_agro_brasil.providers.noticias_agricolas import (
    _PADRAO_DATA_VALOR,
    _extrair_valor_estado_leite,
    _parse_valor,
    buscar_cotacao_leite,
    buscar_cotacao_milho,
    buscar_cotacao_soja,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _html_soja() -> str:
    return (FIXTURES / "soja_cepea.html").read_text(encoding="utf-8")


def _html_milho() -> str:
    return (FIXTURES / "milho_cepea.html").read_text(encoding="utf-8")


def _html_leite() -> str:
    return (FIXTURES / "leite_cepea_rs.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Utilitários de parsing
# ---------------------------------------------------------------------------


class TestParseValor:
    def test_virgula_decimal(self) -> None:
        assert _parse_valor("133,87") == pytest.approx(133.87)

    def test_decimal_leite(self) -> None:
        assert _parse_valor("2,5169") == pytest.approx(2.5169)

    def test_ponto_milhar(self) -> None:
        assert _parse_valor("1.133,87") == pytest.approx(1133.87)

    def test_inteiro(self) -> None:
        assert _parse_valor("63") == pytest.approx(63.0)


# ---------------------------------------------------------------------------
# Soja
# ---------------------------------------------------------------------------


class TestSojaParsing:
    def test_extrai_valor_mais_recente(self) -> None:
        match = _PADRAO_DATA_VALOR.search(_html_soja())
        assert match is not None
        assert _parse_valor(match.group(1)) == pytest.approx(133.87)

    def test_html_vazio_nao_tem_match(self) -> None:
        assert _PADRAO_DATA_VALOR.search("<html>sem cotacao</html>") is None


class TestSojaBusca:
    def test_retorna_campos_obrigatorios(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        class MockResponse:
            text = _html_soja()
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

        resultado = buscar_cotacao_soja()
        assert resultado["a_vista"] == pytest.approx(133.87)
        assert resultado["moeda"] == "BRL"
        assert resultado["unidade"] == "saca"
        assert "CEPEA" in str(resultado["fonte"])
        assert "Soja" in str(resultado["indicador"])

    def test_retorna_none_quando_sem_dados(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import httpx

        class MockResponse:
            text = "<html>sem cotacao</html>"
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

        resultado = buscar_cotacao_soja()
        assert resultado["a_vista"] is None


# ---------------------------------------------------------------------------
# Milho
# ---------------------------------------------------------------------------


class TestMilhoParsing:
    def test_extrai_valor_mais_recente(self) -> None:
        match = _PADRAO_DATA_VALOR.search(_html_milho())
        assert match is not None
        assert _parse_valor(match.group(1)) == pytest.approx(63.45)

    def test_html_vazio_nao_tem_match(self) -> None:
        assert _PADRAO_DATA_VALOR.search("<html>sem cotacao</html>") is None


class TestMilhoBusca:
    def test_retorna_campos_obrigatorios(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        class MockResponse:
            text = _html_milho()
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

        resultado = buscar_cotacao_milho()
        assert resultado["a_vista"] == pytest.approx(63.45)
        assert resultado["moeda"] == "BRL"
        assert resultado["unidade"] == "saca"
        assert "CEPEA" in str(resultado["fonte"])
        assert "Milho" in str(resultado["indicador"])


# ---------------------------------------------------------------------------
# Leite
# ---------------------------------------------------------------------------


class TestLeiteParsing:
    def test_extrai_brasil(self) -> None:
        val = _extrair_valor_estado_leite(_html_leite(), "Brasil")
        assert val == pytest.approx(2.6584)

    def test_extrai_go(self) -> None:
        val = _extrair_valor_estado_leite(_html_leite(), "GO")
        assert val == pytest.approx(2.5894)

    def test_extrai_mg(self) -> None:
        val = _extrair_valor_estado_leite(_html_leite(), "MG")
        assert val == pytest.approx(2.7534)

    def test_estado_inexistente_retorna_none(self) -> None:
        val = _extrair_valor_estado_leite(_html_leite(), "XX")
        assert val is None

    def test_case_insensitive(self) -> None:
        val = _extrair_valor_estado_leite(_html_leite(), "go")
        assert val == pytest.approx(2.5894)


class TestLeiteBusca:
    def test_retorna_brasil_por_padrao(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        class MockResponse:
            text = _html_leite()
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

        resultado = buscar_cotacao_leite()
        assert resultado["a_vista"] == pytest.approx(2.6584)
        assert resultado["estado"] == "Brasil"
        assert resultado["unidade"] == "L"
        assert resultado["moeda"] == "BRL"
        assert "CEPEA" in str(resultado["fonte"])

    def test_retorna_estado_go(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        class MockResponse:
            text = _html_leite()
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

        resultado = buscar_cotacao_leite("GO")
        assert resultado["a_vista"] == pytest.approx(2.5894)
        assert resultado["estado"] == "GO"
