"""Testes do provider RSS de notícias do agronegócio usando fixture XML."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_agro_brasil.providers.rss_agro import _parsear_itens, buscar_noticias

FIXTURES = Path(__file__).parent / "fixtures"


def _xml_canal_rural() -> str:
    return (FIXTURES / "canal_rural_rss.xml").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# _parsear_itens
# ---------------------------------------------------------------------------


class TestParsearItens:
    def test_extrai_cinco_itens_da_fixture(self) -> None:
        itens = _parsear_itens(_xml_canal_rural(), "Canal Rural")
        assert len(itens) == 5

    def test_campos_obrigatorios_presentes(self) -> None:
        itens = _parsear_itens(_xml_canal_rural(), "Canal Rural")
        for item in itens:
            assert "titulo" in item
            assert "link" in item
            assert "data" in item
            assert "fonte" in item
            assert item["fonte"] == "Canal Rural"

    def test_titulo_nao_vazio(self) -> None:
        itens = _parsear_itens(_xml_canal_rural(), "Canal Rural")
        for item in itens:
            assert len(item["titulo"]) > 0

    def test_link_comeca_com_https(self) -> None:
        itens = _parsear_itens(_xml_canal_rural(), "Canal Rural")
        for item in itens:
            assert item["link"].startswith("https://")

    def test_xml_vazio_retorna_lista_vazia(self) -> None:
        xml_sem_canal = "<?xml version='1.0'?><rss version='2.0'></rss>"
        itens = _parsear_itens(xml_sem_canal, "Teste")
        assert itens == []

    def test_descricao_truncada_em_200_chars(self) -> None:
        itens = _parsear_itens(_xml_canal_rural(), "Canal Rural")
        for item in itens:
            assert len(item["descricao"]) <= 200


# ---------------------------------------------------------------------------
# buscar_noticias - sem filtro
# ---------------------------------------------------------------------------


class TestBuscarNoticias:
    def _mock_httpx(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        class MockResponse:
            text = _xml_canal_rural()
            status_code = 200

            def raise_for_status(self) -> None:
                pass

        class MockClient:
            def __enter__(self) -> MockClient:
                return self

            def __exit__(self, *args: object) -> None:
                pass

            def get(self, url: str) -> MockResponse:
                return MockResponse()

        monkeypatch.setattr(httpx, "Client", lambda **kw: MockClient())

    def test_retorna_campos_obrigatorios(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._mock_httpx(monkeypatch)
        resultado = buscar_noticias()

        assert "noticias" in resultado
        assert "total" in resultado
        assert "feeds_consultados" in resultado
        assert "data_consulta" in resultado
        assert isinstance(resultado["noticias"], list)

    def test_limite_padrao_cinco(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._mock_httpx(monkeypatch)
        resultado = buscar_noticias()
        assert resultado["total"] == 5
        assert len(resultado["noticias"]) == 5

    def test_limite_customizado(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._mock_httpx(monkeypatch)
        resultado = buscar_noticias(limite=3)
        assert len(resultado["noticias"]) == 3

    def test_limite_maximo_20(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._mock_httpx(monkeypatch)
        # Fixture tem 5 itens, mas limita em 20 max (não deve estourar)
        resultado = buscar_noticias(limite=25)
        assert len(resultado["noticias"]) <= 5  # fixture tem só 5

    def test_feeds_consultados_nao_vazio(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._mock_httpx(monkeypatch)
        resultado = buscar_noticias()
        assert len(resultado["feeds_consultados"]) >= 1
        assert "Canal Rural" in resultado["feeds_consultados"]


# ---------------------------------------------------------------------------
# buscar_noticias - com filtro de tema
# ---------------------------------------------------------------------------


class TestBuscarNoticiasFiltro:
    def _mock_httpx(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        class MockResponse:
            text = _xml_canal_rural()
            status_code = 200

            def raise_for_status(self) -> None:
                pass

        class MockClient:
            def __enter__(self) -> MockClient:
                return self

            def __exit__(self, *args: object) -> None:
                pass

            def get(self, url: str) -> MockResponse:
                return MockResponse()

        monkeypatch.setattr(httpx, "Client", lambda **kw: MockClient())

    def test_filtra_por_soja(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._mock_httpx(monkeypatch)
        resultado = buscar_noticias(tema="soja")
        assert resultado["tema_filtro"] == "soja"
        for noticia in resultado["noticias"]:
            assert "soja" in noticia["titulo"].lower()

    def test_filtra_por_milho(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._mock_httpx(monkeypatch)
        resultado = buscar_noticias(tema="milho")
        for noticia in resultado["noticias"]:
            assert "milho" in noticia["titulo"].lower()

    def test_tema_sem_resultado_retorna_lista_vazia(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._mock_httpx(monkeypatch)
        resultado = buscar_noticias(tema="abacaxi_improbavel_xyz")
        assert resultado["total"] == 0
        assert resultado["noticias"] == []

    def test_tema_none_retorna_todas(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._mock_httpx(monkeypatch)
        resultado = buscar_noticias(tema=None, limite=10)
        assert resultado["tema_filtro"] is None
        assert resultado["total"] == 5  # fixture tem 5 itens


# ---------------------------------------------------------------------------
# buscar_noticias - falha de rede
# ---------------------------------------------------------------------------


class TestBuscarNoticiasErro:
    def test_levanta_runtimeerror_quando_feed_falha(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import httpx

        class MockClient:
            def __enter__(self) -> MockClient:
                return self

            def __exit__(self, *args: object) -> None:
                pass

            def get(self, url: str) -> None:
                raise httpx.ConnectError("timeout simulado")

        monkeypatch.setattr(httpx, "Client", lambda **kw: MockClient())

        with pytest.raises(RuntimeError, match="falharam"):
            buscar_noticias()
