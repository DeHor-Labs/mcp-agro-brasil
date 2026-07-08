"""Testes do comando de dump JSON (python -m mcp_agro_brasil.dump).

Todo o tráfego HTTP é interceptado via monkeypatch de httpx.Client roteando
por fragmento de URL para as fixtures locais. Zero rede.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from mcp_agro_brasil.core import cotacao
from mcp_agro_brasil.dump import main, normalizar_fonte

FIXTURES = Path(__file__).parent / "fixtures"

# Fragmento de URL -> arquivo de fixture servido.
_ROTAS: tuple[tuple[str, str], ...] = (
    ("scotconsultoria", "scot_boi_gordo.html"),
    ("boi-gordo-indicador-esalq", "esalq_boi_gordo.html"),
    ("soja-indicador-cepea", "soja_cepea.html"),
    ("indicador-cepea-esalq-milho", "milho_cepea.html"),
    ("leite-precos-ao-produtor", "leite_cepea_rs.html"),
)


class _MockResponse:
    status_code = 200

    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        pass


class _MockClient:
    """Cliente httpx falso que serve fixtures por fragmento de URL.

    URLs cujo fragmento esteja em `fora_do_ar` levantam erro de conexão,
    simulando provider indisponível.
    """

    def __init__(self, fora_do_ar: tuple[str, ...] = ()) -> None:
        self._fora_do_ar = fora_do_ar

    def __enter__(self) -> _MockClient:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def get(self, url: str) -> _MockResponse:
        for fragmento in self._fora_do_ar:
            if fragmento in url:
                raise httpx.ConnectError("provider fora do ar (simulado)")
        for fragmento, arquivo in _ROTAS:
            if fragmento in url:
                return _MockResponse((FIXTURES / arquivo).read_text(encoding="utf-8"))
        raise AssertionError(f"URL sem rota de fixture no teste: {url}")


@pytest.fixture(autouse=True)
def _cache_limpo() -> None:
    """O cache do core é global ao processo; limpa entre testes."""
    cotacao._CACHE.clear()


def _mock_rede(monkeypatch: pytest.MonkeyPatch, fora_do_ar: tuple[str, ...] = ()) -> None:
    monkeypatch.setattr(httpx, "Client", lambda **kw: _MockClient(fora_do_ar))


def _rodar(capsys: pytest.CaptureFixture[str], argv: list[str]) -> tuple[int, dict[str, Any]]:
    codigo = main(argv)
    saida = capsys.readouterr().out
    payload: dict[str, Any] = json.loads(saida)
    return codigo, payload


def _por_chave(payload: dict[str, Any], produto: str, nivel: str) -> dict[str, Any]:
    achados = [i for i in payload["itens"] if i["produto"] == produto and i["nivel"] == nivel]
    assert len(achados) == 1, f"esperado 1 item {produto}/{nivel}, veio {len(achados)}"
    item: dict[str, Any] = achados[0]
    return item


# ---------------------------------------------------------------------------
# Normalização de fonte
# ---------------------------------------------------------------------------


class TestNormalizarFonte:
    def test_scot(self) -> None:
        assert normalizar_fonte("Scot Consultoria") == "Scot Consultoria"

    def test_esalq_b3(self) -> None:
        assert normalizar_fonte("ESALQ/B3 via Notícias Agrícolas") == "ESALQ/B3"

    def test_cepea_esalq_graos(self) -> None:
        assert normalizar_fonte("CEPEA/ESALQ via Notícias Agrícolas") == "CEPEA"

    def test_cepea_leite(self) -> None:
        assert normalizar_fonte("CEPEA via Notícias Agrícolas") == "CEPEA"

    def test_desconhecida_passa_como_veio(self) -> None:
        assert normalizar_fonte("Fonte Nova XYZ") == "Fonte Nova XYZ"


# ---------------------------------------------------------------------------
# Dump completo: formato do contrato
# ---------------------------------------------------------------------------


class TestDumpCompleto:
    def test_contrato_completo(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _mock_rede(monkeypatch)
        codigo, payload = _rodar(
            capsys,
            ["--produtos", "boi_gordo,soja,milho,leite", "--leite-estados", "GO"],
        )

        assert codigo == 0
        assert set(payload.keys()) == {"gerado_em", "itens", "erros"}
        assert payload["erros"] == []

        gerado_em = datetime.fromisoformat(payload["gerado_em"])
        assert gerado_em.tzinfo is not None

        boi_br = _por_chave(payload, "boi_gordo", "br")
        assert boi_br["valor"] == pytest.approx(338.65)
        assert boi_br["unidade"] == "@"
        assert boi_br["fonte"] == "ESALQ/B3"
        assert boi_br["uf"] is None
        assert boi_br["localidade"] is None

        boi_go = _por_chave(payload, "boi_gordo", "municipio")
        assert boi_go["valor"] == pytest.approx(316.50)
        assert boi_go["fonte"] == "Scot Consultoria"
        assert boi_go["uf"] == "GO"
        assert boi_go["localidade"] == "GOIANIA"

        soja = _por_chave(payload, "soja", "br")
        assert soja["valor"] == pytest.approx(133.87)
        assert soja["unidade"] == "saca 60kg"
        assert soja["fonte"] == "CEPEA"

        milho = _por_chave(payload, "milho", "br")
        assert milho["valor"] == pytest.approx(63.45)
        assert milho["unidade"] == "saca 60kg"

        leite_go = _por_chave(payload, "leite", "uf")
        assert leite_go["valor"] == pytest.approx(2.5894)
        assert leite_go["unidade"] == "litro"
        assert leite_go["fonte"] == "CEPEA"
        assert leite_go["uf"] == "GO"

        leite_br = _por_chave(payload, "leite", "br")
        assert leite_br["valor"] == pytest.approx(2.6584)
        assert leite_br["uf"] is None

        for item in payload["itens"]:
            assert set(item.keys()) == {
                "produto",
                "valor",
                "unidade",
                "fonte",
                "data",
                "nivel",
                "uf",
                "localidade",
            }
            assert isinstance(item["valor"], float)
            datetime.strptime(item["data"], "%Y-%m-%d")


# ---------------------------------------------------------------------------
# Sucesso parcial e exit codes
# ---------------------------------------------------------------------------


class TestSucessoParcial:
    def test_boi_fora_do_ar_demais_saem(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _mock_rede(
            monkeypatch,
            fora_do_ar=("scotconsultoria", "boi-gordo-indicador-esalq"),
        )
        codigo, payload = _rodar(
            capsys,
            ["--produtos", "boi_gordo,soja,milho,leite", "--leite-estados", "GO"],
        )

        assert codigo == 0
        produtos_com_item = {i["produto"] for i in payload["itens"]}
        assert produtos_com_item == {"soja", "milho", "leite"}
        assert len(payload["erros"]) == 1
        assert payload["erros"][0]["produto"] == "boi_gordo"
        assert "fora do ar" in payload["erros"][0]["motivo"]

    def test_scot_fora_emite_so_nacional(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _mock_rede(monkeypatch, fora_do_ar=("scotconsultoria",))
        codigo, payload = _rodar(capsys, ["--produtos", "boi_gordo"])

        assert codigo == 0
        assert payload["erros"] == []
        niveis = [i["nivel"] for i in payload["itens"]]
        assert niveis == ["br"]

    def test_todos_falham_exit_1(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _mock_rede(
            monkeypatch,
            fora_do_ar=tuple(fragmento for fragmento, _ in _ROTAS),
        )
        codigo, payload = _rodar(
            capsys,
            ["--produtos", "boi_gordo,soja,milho,leite", "--leite-estados", "GO"],
        )

        assert codigo == 1
        assert payload["itens"] == []
        assert {e["produto"] for e in payload["erros"]} == {
            "boi_gordo",
            "soja",
            "milho",
            "leite",
        }

    def test_praca_falha_indicador_ok_gera_erro_parcial(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _mock_rede(monkeypatch)

        def _explode(praca: str) -> dict[str, Any]:
            raise RuntimeError("praça indisponível (simulado)")

        monkeypatch.setattr(cotacao, "cotacao_boi_gordo", _explode)
        codigo, payload = _rodar(capsys, ["--produtos", "boi_gordo"])

        # Indicador nacional saiu, praça Goiânia falhou: item mantido e
        # sub-falha exposta em erros com o prefixo "parcial: ".
        assert codigo == 0
        assert [i["nivel"] for i in payload["itens"]] == ["br"]
        assert payload["erros"] == [
            {
                "produto": "boi_gordo",
                "motivo": "parcial: praça Goiânia: praça indisponível (simulado)",
            }
        ]

    def test_produto_desconhecido_vai_para_erros(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _mock_rede(monkeypatch)
        codigo, payload = _rodar(capsys, ["--produtos", "soja,cacau"])

        assert codigo == 0
        assert {e["produto"] for e in payload["erros"]} == {"cacau"}
        assert "desconhecido" in payload["erros"][0]["motivo"]


# ---------------------------------------------------------------------------
# Leite: estados pedidos via --leite-estados
# ---------------------------------------------------------------------------


class TestLeiteEstados:
    def test_go_mais_brasil(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _mock_rede(monkeypatch)
        codigo, payload = _rodar(capsys, ["--produtos", "leite", "--leite-estados", "GO"])

        assert codigo == 0
        assert payload["erros"] == []
        assert len(payload["itens"]) == 2
        assert {(i["nivel"], i["uf"]) for i in payload["itens"]} == {
            ("uf", "GO"),
            ("br", None),
        }

    def test_sem_estados_so_brasil(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _mock_rede(monkeypatch)
        codigo, payload = _rodar(capsys, ["--produtos", "leite"])

        assert codigo == 0
        assert [i["nivel"] for i in payload["itens"]] == ["br"]

    def test_estado_fora_da_tabela_nao_derruba(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _mock_rede(monkeypatch)
        codigo, payload = _rodar(capsys, ["--produtos", "leite", "--leite-estados", "XX,GO"])

        # XX não existe na tabela, mas GO e Brasil saem; produto teve sucesso
        # parcial. O estado ausente deve aparecer em erros, não sumir.
        assert codigo == 0
        assert {(i["nivel"], i["uf"]) for i in payload["itens"]} == {
            ("uf", "GO"),
            ("br", None),
        }
        assert len(payload["erros"]) == 1
        assert payload["erros"][0]["produto"] == "leite"
        assert payload["erros"][0]["motivo"].startswith("parcial: ")
        assert "XX" in payload["erros"][0]["motivo"]
