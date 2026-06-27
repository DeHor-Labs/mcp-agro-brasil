"""Testes dos providers Open-Meteo (clima) e BCB (câmbio PTAX) usando fixtures JSON (sem rede)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_agro_brasil.providers.bcb import buscar_ptax
from mcp_agro_brasil.providers.open_meteo import _buscar_coordenadas, buscar_previsao

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture_geocoding() -> dict:
    return json.loads((FIXTURES / "open_meteo_geocoding.json").read_text())


def _fixture_forecast() -> dict:
    return json.loads((FIXTURES / "open_meteo_forecast.json").read_text())


def _fixture_ptax() -> dict:
    return json.loads((FIXTURES / "bcb_ptax.json").read_text())


# ---------------------------------------------------------------------------
# Testes Open-Meteo: geocoding
# ---------------------------------------------------------------------------


class TestOpenMeteoGeocoding:
    def test_coordenadas_goiania(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Resolve Goiânia para lat/lon corretos via fixture."""
        import httpx

        mock_resp = MagicMock()
        mock_resp.json.return_value = _fixture_geocoding()
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        monkeypatch.setattr(httpx, "Client", lambda **kw: mock_client)

        resultado = _buscar_coordenadas("Goiânia")
        assert resultado["latitude"] == pytest.approx(-16.67861)
        assert resultado["longitude"] == pytest.approx(-49.25389)
        assert resultado["nome_resolvido"] == "Goiânia"

    def test_cidade_nao_encontrada_levanta_valueerror(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import httpx

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        monkeypatch.setattr(httpx, "Client", lambda **kw: mock_client)

        with pytest.raises(ValueError, match="não encontrada"):
            _buscar_coordenadas("CidadeXXInexistente")


# ---------------------------------------------------------------------------
# Testes Open-Meteo: previsão
# ---------------------------------------------------------------------------


class TestOpenMeteoPrevisao:
    def _patch_httpx(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Monta mock duplo: geocoding e forecast."""
        import httpx

        geo_resp = MagicMock()
        geo_resp.json.return_value = _fixture_geocoding()
        geo_resp.raise_for_status = MagicMock()

        forecast_resp = MagicMock()
        forecast_resp.json.return_value = _fixture_forecast()
        forecast_resp.raise_for_status = MagicMock()

        # Primeira chamada = geocoding, segunda = forecast
        call_count = {"n": 0}

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        def fake_get(url: str, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return geo_resp
            return forecast_resp

        mock_client.get.side_effect = fake_get
        monkeypatch.setattr(httpx, "Client", lambda **kw: mock_client)

    def test_previsao_retorna_campos_obrigatorios(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_httpx(monkeypatch)
        resultado = buscar_previsao("Goiânia", dias=5)
        assert resultado["fonte"] == "Open-Meteo"
        assert resultado["cidade"] == "Goiânia"
        assert resultado["cidade_resolvida"] == "Goiânia"
        assert "dias" in resultado
        assert "data_consulta" in resultado

    def test_previsao_tem_5_dias(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_httpx(monkeypatch)
        resultado = buscar_previsao("Goiânia", dias=5)
        assert len(resultado["dias"]) == 5

    def test_previsao_primeiro_dia_campos(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_httpx(monkeypatch)
        resultado = buscar_previsao("Goiânia", dias=5)
        dia = resultado["dias"][0]
        assert dia["data"] == "2026-06-27"
        assert dia["temp_max_c"] == pytest.approx(29.2)
        assert dia["temp_min_c"] == pytest.approx(17.9)
        assert dia["precipitacao_mm"] == pytest.approx(0.0)
        assert dia["prob_chuva_pct"] == 0

    def test_dias_limite_superior_truncado_a_7(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_httpx(monkeypatch)
        # dias=10 deve ser truncado para 7 internamente
        resultado = buscar_previsao("Goiânia", dias=10)
        assert len(resultado["dias"]) <= 7

    def test_dias_limite_inferior_minimo_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_httpx(monkeypatch)
        resultado = buscar_previsao("Goiânia", dias=0)
        assert len(resultado["dias"]) >= 1


# ---------------------------------------------------------------------------
# Testes BCB PTAX
# ---------------------------------------------------------------------------


class TestBcbPtax:
    def _patch_httpx(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        mock_resp = MagicMock()
        mock_resp.json.return_value = _fixture_ptax()
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        monkeypatch.setattr(httpx, "Client", lambda **kw: mock_client)

    def test_ptax_retorna_campos_obrigatorios(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_httpx(monkeypatch)
        resultado = buscar_ptax()
        assert resultado["moeda_origem"] == "USD"
        assert resultado["moeda_destino"] == "BRL"
        assert "compra" in resultado
        assert "venda" in resultado
        assert "data_hora_cotacao" in resultado
        assert "data_consulta" in resultado
        assert "Banco Central" in resultado["fonte"]

    def test_ptax_compra_venda_corretos(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_httpx(monkeypatch)
        resultado = buscar_ptax()
        assert resultado["compra"] == pytest.approx(5.1689)
        assert resultado["venda"] == pytest.approx(5.1695)

    def test_ptax_venda_maior_ou_igual_compra(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._patch_httpx(monkeypatch)
        resultado = buscar_ptax()
        assert resultado["venda"] >= resultado["compra"]

    def test_ptax_sem_cotacao_levanta_runtimeerror(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"value": []}
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        monkeypatch.setattr(httpx, "Client", lambda **kw: mock_client)

        with pytest.raises(RuntimeError, match="PTAX indisponível"):
            buscar_ptax()
