"""Testes do calendário de safra (CONAB) e futuros B3."""

from __future__ import annotations

import pytest

from mcp_agro_brasil.core.calendario_safra import (
    CULTURAS,
    REGIOES,
    _meses_para_texto,
    _normalizar_cultura,
    _normalizar_regiao,
    consultar_calendario_safra,
)
from mcp_agro_brasil.core.cotacao import calendario_safra_consulta, futuros_b3

# ---------------------------------------------------------------------------
# Utilitários internos
# ---------------------------------------------------------------------------


class TestNormalizarCultura:
    def test_nome_canonico(self) -> None:
        assert _normalizar_cultura("soja") == "soja"
        assert _normalizar_cultura("feijao") == "feijao"
        assert _normalizar_cultura("sorgo") == "sorgo"

    def test_alias_milho_retorna_milho_1a(self) -> None:
        assert _normalizar_cultura("milho") == "milho_1a"

    def test_alias_safrinha_retorna_milho_2a(self) -> None:
        assert _normalizar_cultura("safrinha") == "milho_2a"
        assert _normalizar_cultura("milho safrinha") == "milho_2a"
        assert _normalizar_cultura("milho_2a") == "milho_2a"

    def test_alias_com_acento(self) -> None:
        assert _normalizar_cultura("feijão") == "feijao"
        assert _normalizar_cultura("café") == "cafe"
        assert _normalizar_cultura("algodão") == "algodao"

    def test_case_insensitive(self) -> None:
        assert _normalizar_cultura("SOJA") == "soja"
        assert _normalizar_cultura("Milho") == "milho_1a"

    def test_cultura_desconhecida_retorna_none(self) -> None:
        assert _normalizar_cultura("trigo") is None
        assert _normalizar_cultura("arroz") is None
        assert _normalizar_cultura("") is None


class TestNormalizarRegiao:
    def test_nome_canonico(self) -> None:
        assert _normalizar_regiao("Centro-Oeste") == "Centro-Oeste"
        assert _normalizar_regiao("Sul") == "Sul"
        assert _normalizar_regiao("Sudeste") == "Sudeste"
        assert _normalizar_regiao("MATOPIBA") == "MATOPIBA"
        assert _normalizar_regiao("Nordeste") == "Nordeste"

    def test_sigla_estado_centro_oeste(self) -> None:
        assert _normalizar_regiao("GO") == "Centro-Oeste"
        assert _normalizar_regiao("MT") == "Centro-Oeste"
        assert _normalizar_regiao("MS") == "Centro-Oeste"

    def test_sigla_estado_sul(self) -> None:
        assert _normalizar_regiao("PR") == "Sul"
        assert _normalizar_regiao("SC") == "Sul"
        assert _normalizar_regiao("RS") == "Sul"

    def test_sigla_estado_sudeste(self) -> None:
        assert _normalizar_regiao("SP") == "Sudeste"
        assert _normalizar_regiao("MG") == "Sudeste"

    def test_sigla_matopiba(self) -> None:
        assert _normalizar_regiao("MA") == "MATOPIBA"
        assert _normalizar_regiao("TO") == "MATOPIBA"
        assert _normalizar_regiao("PI") == "MATOPIBA"

    def test_sigla_nordeste(self) -> None:
        assert _normalizar_regiao("BA") == "Nordeste"

    def test_case_insensitive(self) -> None:
        assert _normalizar_regiao("go") == "Centro-Oeste"
        assert _normalizar_regiao("sul") == "Sul"

    def test_regiao_desconhecida_retorna_none(self) -> None:
        assert _normalizar_regiao("AM") is None
        assert _normalizar_regiao("XYZ") is None


class TestMesesParaTexto:
    def test_lista_simples(self) -> None:
        resultado = _meses_para_texto([10, 11, 12])
        assert "out" in resultado
        assert "nov" in resultado
        assert "dez" in resultado

    def test_lista_vazia_retorna_nao_cadastrado(self) -> None:
        assert _meses_para_texto([]) == "não cadastrado"

    def test_deduplicacao(self) -> None:
        resultado = _meses_para_texto([1, 1, 2])
        assert resultado.count("jan") == 1


# ---------------------------------------------------------------------------
# Consulta ao calendário
# ---------------------------------------------------------------------------


class TestConsultarCalendarioSafra:
    def test_soja_centro_oeste_retorna_resultado(self) -> None:
        resp = consultar_calendario_safra("soja", "Centro-Oeste")
        assert resp["resultado"] is not None
        resultado = resp["resultado"]
        assert resultado["regiao"] == "Centro-Oeste"
        assert "out" in resultado["plantio_meses"]
        assert "jan" in resultado["colheita_meses"]

    def test_soja_centro_oeste_via_sigla_go(self) -> None:
        resp = consultar_calendario_safra("soja", "GO")
        assert resp["resultado"] is not None
        assert resp["resultado"]["regiao"] == "Centro-Oeste"

    def test_milho_alias_retorna_milho_1a(self) -> None:
        resp = consultar_calendario_safra("milho", "PR")
        assert resp["cultura_normalizada"] == "milho_1a"
        assert resp["resultado"] is not None

    def test_safrinha_alias_retorna_milho_2a(self) -> None:
        resp = consultar_calendario_safra("safrinha", "Centro-Oeste")
        assert resp["cultura_normalizada"] == "milho_2a"
        assert resp["resultado"] is not None
        # plantio em jan-mar
        assert "jan" in resp["resultado"]["plantio_meses"]

    def test_sem_regiao_retorna_todas_regioes(self) -> None:
        resp = consultar_calendario_safra("soja")
        assert "regioes" in resp
        assert len(resp["regioes"]) == len(REGIOES)

    def test_cafe_matopiba_sem_dados(self) -> None:
        resp = consultar_calendario_safra("cafe", "MATOPIBA")
        # Tem resultado mas plantio/colheita vazios (não cadastrado)
        resultado = resp["resultado"]
        assert resultado is not None
        assert resultado["plantio_meses"] == "não cadastrado"
        assert resultado["colheita_meses"] == "não cadastrado"

    def test_algodao_sul_sem_dados(self) -> None:
        resp = consultar_calendario_safra("algodao", "Sul")
        resultado = resp["resultado"]
        assert resultado is not None
        assert resultado["plantio_meses"] == "não cadastrado"

    def test_cultura_invalida_levanta_value_error(self) -> None:
        with pytest.raises(ValueError, match="não reconhecida"):
            consultar_calendario_safra("trigo", "Sul")

    def test_regiao_invalida_retorna_aviso(self) -> None:
        resp = consultar_calendario_safra("soja", "AM")
        assert resp["resultado"] is None
        assert "aviso" in resp

    def test_fonte_referencia_conab(self) -> None:
        resp = consultar_calendario_safra("soja", "GO")
        assert "CONAB" in resp["fonte"]

    def test_campos_obrigatorios_presentes(self) -> None:
        resp = consultar_calendario_safra("soja", "GO")
        for campo in (
            "cultura_consultada",
            "cultura_normalizada",
            "fonte",
            "data_consulta",
        ):
            assert campo in resp

    def test_todas_culturas_disponiveis(self) -> None:
        for cultura in CULTURAS:
            resp = consultar_calendario_safra(cultura)
            assert resp["cultura_normalizada"] == cultura
            assert len(resp["regioes"]) > 0

    def test_feijao_com_acento_alias(self) -> None:
        resp = consultar_calendario_safra("feijão", "MG")
        assert resp["cultura_normalizada"] == "feijao"
        assert resp["resultado"] is not None


# ---------------------------------------------------------------------------
# Wrapper em cotacao.py
# ---------------------------------------------------------------------------


class TestCalendarioSafraCotacao:
    def test_wrapper_retorna_mesmo_resultado(self) -> None:
        direto = consultar_calendario_safra("soja", "GO")
        via_wrapper = calendario_safra_consulta("soja", "GO")
        assert direto["resultado"] == via_wrapper["resultado"]

    def test_wrapper_sem_regiao(self) -> None:
        resp = calendario_safra_consulta("milho")
        assert "regioes" in resp


# ---------------------------------------------------------------------------
# Futuros B3
# ---------------------------------------------------------------------------


class TestFuturosB3:
    def test_retorna_disponivel_false(self) -> None:
        resp = futuros_b3("BGI")
        assert resp["disponivel"] is False

    def test_contrato_normalizado_maiusculo(self) -> None:
        resp = futuros_b3("bgi")
        assert resp["contrato"] == "BGI"

    def test_contrato_info_bgi(self) -> None:
        resp = futuros_b3("BGI")
        info = resp["contrato_info"]
        assert info is not None
        assert info["codigo"] == "BGI"
        assert "Boi Gordo" in info["descricao"]

    def test_contrato_info_ccm(self) -> None:
        resp = futuros_b3("CCM")
        assert resp["contrato_info"] is not None
        assert resp["contrato_info"]["codigo"] == "CCM"

    def test_contrato_info_sfi(self) -> None:
        resp = futuros_b3("SFI")
        assert resp["contrato_info"] is not None
        assert "Soja" in resp["contrato_info"]["descricao"]

    def test_contrato_info_icf(self) -> None:
        resp = futuros_b3("ICF")
        assert resp["contrato_info"] is not None
        assert "Café" in resp["contrato_info"]["descricao"]

    def test_contrato_desconhecido_info_none(self) -> None:
        resp = futuros_b3("XYZ")
        assert resp["contrato_info"] is None

    def test_aviso_menciona_brapi(self) -> None:
        resp = futuros_b3("BGI")
        assert "brapi" in resp["aviso"].lower()

    def test_aviso_menciona_fonte_paga(self) -> None:
        resp = futuros_b3("BGI")
        assert "401" in resp["aviso"] or "pago" in resp["aviso"].lower()

    def test_contratos_suportados_lista(self) -> None:
        resp = futuros_b3()
        assert isinstance(resp["contratos_suportados"], list)
        codigos = [c["codigo"] for c in resp["contratos_suportados"]]
        assert "BGI" in codigos
        assert "CCM" in codigos
        assert "SFI" in codigos
        assert "ICF" in codigos

    def test_alternativa_vista_presente(self) -> None:
        resp = futuros_b3("BGI")
        assert "cotacao_boi_gordo" in resp["alternativa_vista"]

    def test_fonte_sugerida_presente(self) -> None:
        resp = futuros_b3()
        assert "brapi" in resp["fonte_sugerida"].lower()

    def test_data_consulta_formato_iso(self) -> None:
        from datetime import date

        resp = futuros_b3()
        assert resp["data_consulta"] == date.today().isoformat()
