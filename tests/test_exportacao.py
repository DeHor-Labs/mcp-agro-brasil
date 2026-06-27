"""Testes do provider Comex Stat (exportação do agronegócio) usando fixture JSON."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_agro_brasil.providers.comex_stat import (
    PRODUTOS_EXPORTACAO,
    _buscar_exportacao_ncms,
    _periodo_mais_recente,
    buscar_exportacao,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture_exportacao() -> dict:
    return json.loads((FIXTURES / "comex_stat_exportacao.json").read_text(encoding="utf-8"))


def _mock_client_post(fixture: dict):
    """Cria mock de httpx.Client que retorna a fixture no POST."""

    class MockResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return fixture

    class MockClient:
        def __enter__(self) -> MockClient:
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def post(self, url: str, **kwargs: object) -> MockResponse:
            return MockResponse()

    return MockClient()


# ---------------------------------------------------------------------------
# Lista de produtos disponíveis
# ---------------------------------------------------------------------------


class TestProdutosExportacao:
    def test_contem_soja(self) -> None:
        assert "soja" in PRODUTOS_EXPORTACAO

    def test_contem_carne_bovina(self) -> None:
        assert "carne_bovina" in PRODUTOS_EXPORTACAO

    def test_contem_milho(self) -> None:
        assert "milho" in PRODUTOS_EXPORTACAO


# ---------------------------------------------------------------------------
# Periodo mais recente
# ---------------------------------------------------------------------------


class TestPeriodoMaisRecente:
    def test_retorna_formato_yyyy_mm(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        fixture_com_dado = {
            "data": {
                "list": [
                    {
                        "year": "2026",
                        "monthNumber": "05",
                        "chapterCode": "12",
                        "metricFOB": "100",
                    }
                ]
            },
            "success": True,
        }

        class MockResp:
            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict:
                return fixture_com_dado

        class MockClient:
            def __enter__(self) -> MockClient:
                return self

            def __exit__(self, *args: object) -> None:
                pass

            def post(self, url: str, **kwargs: object) -> MockResp:
                return MockResp()

        monkeypatch.setattr(httpx, "Client", lambda **kw: MockClient())
        periodo = _periodo_mais_recente()
        partes = periodo.split("-")
        assert len(partes) == 2
        assert len(partes[0]) == 4  # YYYY
        assert len(partes[1]) == 2  # MM


# ---------------------------------------------------------------------------
# buscar_exportacao_ncms
# ---------------------------------------------------------------------------


class TestBuscarExportacaoNcms:
    def test_retorna_lista_de_registros(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        fixture = _fixture_exportacao()
        monkeypatch.setattr(httpx, "Client", lambda **kw: _mock_client_post(fixture))

        registros = _buscar_exportacao_ncms(["12019000"], "2026-05")
        assert isinstance(registros, list)
        soja = [r for r in registros if r.get("coNcm") == "12019000"]
        assert len(soja) == 1
        assert int(soja[0]["metricFOB"]) > 0

    def test_retorna_lista_vazia_quando_sem_dados(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        fixture_vazia = {"data": {"list": []}, "success": True}
        monkeypatch.setattr(httpx, "Client", lambda **kw: _mock_client_post(fixture_vazia))

        registros = _buscar_exportacao_ncms(["99999999"], "2020-01")
        assert registros == []


# ---------------------------------------------------------------------------
# buscar_exportacao - soja
# ---------------------------------------------------------------------------


class TestBuscarExportacaoSoja:
    def _monkeypatch_comex(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        fixture = _fixture_exportacao()

        # _periodo_mais_recente também faz POST; retornamos um fixture válido pra ele
        fixture_periodo = {
            "data": {
                "list": [
                    {
                        "year": "2026",
                        "monthNumber": "05",
                        "chapterCode": "12",
                        "metricFOB": "100",
                    }
                ]
            },
            "success": True,
        }

        call_count = [0]

        class MockResp:
            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict:
                call_count[0] += 1
                # Primeira chamada: detecção de período; demais: dados reais
                if call_count[0] == 1:
                    return fixture_periodo
                return fixture

        class MockClient:
            def __enter__(self) -> MockClient:
                return self

            def __exit__(self, *args: object) -> None:
                pass

            def post(self, url: str, **kwargs: object) -> MockResp:
                return MockResp()

        monkeypatch.setattr(httpx, "Client", lambda **kw: MockClient())

    def test_retorna_campos_obrigatorios(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._monkeypatch_comex(monkeypatch)
        resultado = buscar_exportacao("soja")

        assert "soja" in resultado["produto"].lower()
        assert resultado["fob_usd"] > 0
        assert resultado["peso_kg"] > 0
        assert resultado["peso_ton"] == pytest.approx(resultado["peso_kg"] / 1000, rel=1e-3)
        assert "MDIC" in str(resultado["fonte"]) or "Comex" in str(resultado["fonte"])
        assert "periodo" in resultado
        assert "ano" in resultado
        assert "mes" in resultado
        assert "data_consulta" in resultado

    def test_produto_desconhecido_levanta_valueerror(self) -> None:
        with pytest.raises(ValueError, match="desconhecido"):
            buscar_exportacao("banana_nanica")


# ---------------------------------------------------------------------------
# buscar_exportacao - carne bovina (soma 2 NCMs)
# ---------------------------------------------------------------------------


class TestBuscarExportacaoCarneBovinaSoma:
    def test_soma_congelada_e_resfriada(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        fixture_periodo = {
            "data": {
                "list": [
                    {
                        "year": "2026",
                        "monthNumber": "05",
                        "chapterCode": "12",
                        "metricFOB": "100",
                    }
                ]
            },
            "success": True,
        }
        fixture_carne = {
            "data": {
                "list": [
                    {
                        "coNcm": "02023000",
                        "year": "2026",
                        "monthNumber": "05",
                        "metricFOB": "1000000",
                        "metricKG": "200000",
                    },
                    {
                        "coNcm": "02013000",
                        "year": "2026",
                        "monthNumber": "05",
                        "metricFOB": "500000",
                        "metricKG": "80000",
                    },
                ]
            },
            "success": True,
        }

        call_count = [0]

        class MockResp:
            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict:
                call_count[0] += 1
                return fixture_periodo if call_count[0] == 1 else fixture_carne

        class MockClient:
            def __enter__(self) -> MockClient:
                return self

            def __exit__(self, *args: object) -> None:
                pass

            def post(self, url: str, **kwargs: object) -> MockResp:
                return MockResp()

        monkeypatch.setattr(httpx, "Client", lambda **kw: MockClient())

        resultado = buscar_exportacao("carne_bovina")
        assert resultado["fob_usd"] == 1_500_000
        assert resultado["peso_kg"] == 280_000
        assert resultado["peso_ton"] == pytest.approx(280.0)


# ---------------------------------------------------------------------------
# buscar_exportacao - milho
# ---------------------------------------------------------------------------


class TestBuscarExportacaoMilho:
    def test_retorna_ncm_correto(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        fixture_periodo = {
            "data": {
                "list": [
                    {
                        "year": "2026",
                        "monthNumber": "05",
                        "chapterCode": "12",
                        "metricFOB": "100",
                    }
                ]
            },
            "success": True,
        }
        fixture_milho = _fixture_exportacao()

        call_count = [0]

        class MockResp:
            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict:
                call_count[0] += 1
                return fixture_periodo if call_count[0] == 1 else fixture_milho

        class MockClient:
            def __enter__(self) -> MockClient:
                return self

            def __exit__(self, *args: object) -> None:
                pass

            def post(self, url: str, **kwargs: object) -> MockResp:
                return MockResp()

        monkeypatch.setattr(httpx, "Client", lambda **kw: MockClient())

        resultado = buscar_exportacao("milho")
        assert "milho" in resultado["produto"].lower() or "10059010" in resultado["ncms"]
        assert resultado["fob_usd"] > 0
