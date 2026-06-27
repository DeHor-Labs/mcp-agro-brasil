"""Testes de conversão de unidades do agronegócio."""

from __future__ import annotations

import pytest

from mcp_agro_brasil.core.conversao import UNIDADES_AREA, UNIDADES_PESO, converter


class TestConversaoPeso:
    def test_arroba_para_kg(self) -> None:
        assert converter(1.0, "@", "kg") == pytest.approx(15.0)

    def test_kg_para_arroba(self) -> None:
        assert converter(15.0, "kg", "@") == pytest.approx(1.0)

    def test_saca_para_kg(self) -> None:
        assert converter(1.0, "saca", "kg") == pytest.approx(60.0)

    def test_kg_para_saca(self) -> None:
        assert converter(60.0, "kg", "saca") == pytest.approx(1.0)

    def test_arroba_para_saca(self) -> None:
        # 1 saca = 60 kg; 1 @ = 15 kg -> 1 saca = 4 arrobas
        assert converter(4.0, "@", "saca") == pytest.approx(1.0)

    def test_tonelada_para_saca(self) -> None:
        # 1 t = 1000 kg; 1 saca = 60 kg -> ~16.667 sacas
        assert converter(1.0, "t", "saca") == pytest.approx(1000.0 / 60.0)

    def test_saca_cafe_verde(self) -> None:
        assert converter(1.0, "saca_cafe_verde", "kg") == pytest.approx(48.0)

    def test_libra_para_kg(self) -> None:
        assert converter(1.0, "lb", "kg") == pytest.approx(0.453592, rel=1e-4)

    def test_case_insensitive(self) -> None:
        assert converter(1.0, "ARROBA", "KG") == pytest.approx(15.0)

    def test_alias_arroba_boi(self) -> None:
        assert converter(1.0, "arroba_boi", "kg") == pytest.approx(15.0)

    def test_mesmo_valor_mesma_unidade(self) -> None:
        assert converter(100.0, "kg", "kg") == pytest.approx(100.0)


class TestConversaoArea:
    def test_hectare_para_m2(self) -> None:
        assert converter(1.0, "ha", "m2") == pytest.approx(10_000.0)

    def test_m2_para_hectare(self) -> None:
        assert converter(10_000.0, "m2", "ha") == pytest.approx(1.0)

    def test_alqueire_goiano_para_hectare(self) -> None:
        # 1 alqueire goiano = 48.400 m² = 4,84 ha
        assert converter(1.0, "alqueire_goiano", "ha") == pytest.approx(4.84)

    def test_alqueire_paulista_para_hectare(self) -> None:
        # 1 alqueire paulista = 24.200 m² = 2,42 ha
        assert converter(1.0, "alqueire_paulista", "ha") == pytest.approx(2.42)

    def test_alqueire_default_e_goiano(self) -> None:
        # "alqueire" sem sufixo = goiano
        assert converter(1.0, "alqueire", "ha") == pytest.approx(
            converter(1.0, "alqueire_goiano", "ha")
        )

    def test_hectare_para_alqueire_goiano(self) -> None:
        assert converter(4.84, "ha", "alqueire_goiano") == pytest.approx(1.0, rel=1e-4)

    def test_acre_para_hectare(self) -> None:
        assert converter(1.0, "acre", "ha") == pytest.approx(0.404686, rel=1e-4)


class TestConversaoErros:
    def test_unidade_origem_desconhecida(self) -> None:
        with pytest.raises(ValueError, match="origem desconhecida"):
            converter(1.0, "xablau", "kg")

    def test_unidade_destino_desconhecida(self) -> None:
        with pytest.raises(ValueError, match="destino desconhecida"):
            converter(1.0, "kg", "xablau")

    def test_conversao_cruzada_peso_area(self) -> None:
        with pytest.raises(ValueError, match="cruzada"):
            converter(1.0, "kg", "ha")

    def test_conversao_cruzada_area_peso(self) -> None:
        with pytest.raises(ValueError, match="cruzada"):
            converter(1.0, "ha", "kg")


class TestListasUnidades:
    def test_unidades_peso_nao_vazio(self) -> None:
        assert len(UNIDADES_PESO) > 0
        assert "@" in UNIDADES_PESO
        assert "kg" in UNIDADES_PESO
        assert "saca" in UNIDADES_PESO

    def test_unidades_area_nao_vazio(self) -> None:
        assert len(UNIDADES_AREA) > 0
        assert "ha" in UNIDADES_AREA
        assert "alqueire_goiano" in UNIDADES_AREA
