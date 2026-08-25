"""Testes da integração opcional com as APIs AgroAPI da Embrapa."""

from __future__ import annotations

from threading import Event, Lock, Thread
from typing import Any

import pytest

from mcp_agro_brasil.providers.agroapi import (
    AgroApiClient,
    AgroApiCredentialsError,
    AgroApiResponse,
    buscar_cultivares_agritec,
    buscar_culturas_agritec,
    buscar_municipios_agritec,
    buscar_produtos_agrofit,
    buscar_produtos_bioinsumos,
    buscar_termos_agrotermos,
    consultar_produto_agrofit,
    consultar_zarc_agritec,
)

_CONCURRENCY_TIMEOUT_SECONDS = 10.0


class RecordingClient:
    """Cliente mínimo para validar rotas e parâmetros sem acessar a rede."""

    def __init__(self, data: Any = None) -> None:
        self.data = [] if data is None else data
        self.calls: list[tuple[str, str, dict[str, str | int | bool]]] = []

    def get(
        self,
        api: str,
        path: str,
        params: dict[str, str | int | bool] | None = None,
    ) -> AgroApiResponse:
        self.calls.append((api, path, params or {}))
        return AgroApiResponse(
            data=self.data,
            pagination={"pagina": 1, "total_registros": 1, "total_paginas": 1},
        )


def test_cliente_sem_credenciais_falha_antes_da_rede(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for nome in (
        "AGROAPI_TOKEN",
        "AGROAPI_ACCESS_TOKEN",
        "AGROAPI_CLIENT_ID",
        "AGROAPI_CONSUMER_KEY",
        "AGROAPI_CLIENT_SECRET",
        "AGROAPI_CONSUMER_SECRET",
    ):
        monkeypatch.delenv(nome, raising=False)

    def fail_on_network(**kwargs: object) -> None:
        raise AssertionError(f"A rede não deveria ser acessada: {kwargs}")

    monkeypatch.setattr("httpx.Client", fail_on_network)

    client = AgroApiClient.from_env()
    with pytest.raises(AgroApiCredentialsError, match="AGROAPI_CLIENT_ID"):
        client.get("agrofit", "/culturas")


def test_cliente_obtem_token_uma_vez_e_reutiliza(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas = {"token": 0, "get": 0}
    headers_recebidos: list[dict[str, str]] = []

    class MockResponse:
        def __init__(self, data: Any, status_code: int = 200) -> None:
            self._data = data
            self.status_code = status_code
            self.headers: dict[str, str] = {}

        def json(self) -> Any:
            return self._data

        def raise_for_status(self) -> None:
            return None

    class MockHttpClient:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

        def __enter__(self) -> MockHttpClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, **kwargs: object) -> MockResponse:
            chamadas["token"] += 1
            assert url == "https://api.cnptia.embrapa.br/token"
            assert kwargs["data"] == {"grant_type": "client_credentials"}
            return MockResponse({"access_token": "token-de-teste", "expires_in": 3600})

        def get(self, url: str, **kwargs: object) -> MockResponse:
            chamadas["get"] += 1
            headers = kwargs["headers"]
            assert isinstance(headers, dict)
            headers_recebidos.append(headers)
            assert url == "https://api.cnptia.embrapa.br/agrofit/v1/culturas"
            return MockResponse([{"nome": "Soja"}])

    import httpx

    monkeypatch.setattr(httpx, "Client", MockHttpClient)
    client = AgroApiClient(client_id="cliente", client_secret="segredo")

    primeira = client.get("agrofit", "/culturas")
    segunda = client.get("agrofit", "/culturas")

    assert primeira.data == [{"nome": "Soja"}]
    assert segunda.data == [{"nome": "Soja"}]
    assert chamadas == {"token": 1, "get": 2}
    assert all(item["Authorization"] == "Bearer token-de-teste" for item in headers_recebidos)


def test_cliente_renova_token_uma_vez_apos_401(monkeypatch: pytest.MonkeyPatch) -> None:
    tokens = iter(("token-a", "token-b"))
    statuses = iter((401, 200))
    autorizacoes: list[str] = []
    chamadas = {"token": 0, "get": 0}

    class MockResponse:
        def __init__(self, data: Any, status_code: int = 200) -> None:
            self._data = data
            self.status_code = status_code
            self.headers: dict[str, str] = {}

        def json(self) -> Any:
            return self._data

        def raise_for_status(self) -> None:
            return None

    class MockHttpClient:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

        def __enter__(self) -> MockHttpClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, **kwargs: object) -> MockResponse:
            chamadas["token"] += 1
            return MockResponse({"access_token": next(tokens), "expires_in": 3600})

        def get(self, url: str, **kwargs: object) -> MockResponse:
            chamadas["get"] += 1
            headers = kwargs["headers"]
            assert isinstance(headers, dict)
            autorizacoes.append(headers["Authorization"])
            return MockResponse([{"nome": "Soja"}], next(statuses))

    monkeypatch.setattr("httpx.Client", MockHttpClient)
    client = AgroApiClient(client_id="cliente", client_secret="segredo")

    resultado = client.get("agrofit", "/culturas")

    assert resultado.data == [{"nome": "Soja"}]
    assert chamadas == {"token": 2, "get": 2}
    assert autorizacoes == ["Bearer token-a", "Bearer token-b"]


def test_cliente_nao_tenta_renovar_token_estatico_em_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chamadas = {"post": 0, "get": 0}

    class MockResponse:
        def __init__(self) -> None:
            self.status_code = 401
            self.headers: dict[str, str] = {}

    class MockHttpClient:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

        def __enter__(self) -> MockHttpClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, **kwargs: object) -> MockResponse:
            chamadas["post"] += 1
            return MockResponse()

        def get(self, url: str, **kwargs: object) -> MockResponse:
            chamadas["get"] += 1
            return MockResponse()

    monkeypatch.setattr("httpx.Client", MockHttpClient)
    client = AgroApiClient(access_token="token-estatico")

    with pytest.raises(AgroApiCredentialsError, match="Token rejeitado"):
        client.get("agrofit", "/culturas")

    assert chamadas == {"post": 0, "get": 1}


def test_cliente_nao_apaga_token_renovado_igual_em_401_atrasado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primeira_requisicao_iniciada = Event()
    token_renovado = Event()
    contador_lock = Lock()
    chamadas = {"token": 0, "get": 0}
    resultados: list[AgroApiResponse] = []
    erros: list[BaseException] = []

    class MockResponse:
        def __init__(self, status_code: int, data: Any = None) -> None:
            self.status_code = status_code
            self._data = [{"nome": "Soja"}] if data is None else data
            self.headers: dict[str, str] = {}

        def json(self) -> Any:
            return self._data

        def raise_for_status(self) -> None:
            return None

    class MockHttpClient:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

        def __enter__(self) -> MockHttpClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, **kwargs: object) -> MockResponse:
            with contador_lock:
                chamadas["token"] += 1
            return MockResponse(
                200,
                {"access_token": "token-repetido", "expires_in": 3600},
            )

        def get(self, url: str, **kwargs: object) -> MockResponse:
            with contador_lock:
                chamadas["get"] += 1
                ordem = chamadas["get"]
            if ordem == 1:
                primeira_requisicao_iniciada.set()
                if not token_renovado.wait(timeout=_CONCURRENCY_TIMEOUT_SECONDS):
                    raise AssertionError("A segunda chamada não renovou o token a tempo")
                return MockResponse(401)
            if ordem == 2:
                return MockResponse(401)
            if ordem == 3:
                token_renovado.set()
            return MockResponse(200)

    def consultar(client: AgroApiClient) -> None:
        try:
            resultados.append(client.get("agrofit", "/culturas"))
        except BaseException as exc:
            erros.append(exc)

    monkeypatch.setattr("httpx.Client", MockHttpClient)
    client = AgroApiClient(client_id="cliente", client_secret="segredo")
    primeira = Thread(target=consultar, args=(client,))
    segunda = Thread(target=consultar, args=(client,))

    primeira.start()
    assert primeira_requisicao_iniciada.wait(timeout=_CONCURRENCY_TIMEOUT_SECONDS)
    segunda.start()
    primeira.join(timeout=_CONCURRENCY_TIMEOUT_SECONDS)
    segunda.join(timeout=_CONCURRENCY_TIMEOUT_SECONDS)

    assert not primeira.is_alive()
    assert not segunda.is_alive()
    assert erros == []
    assert len(resultados) == 2
    assert chamadas == {"token": 2, "get": 4}


def test_agrofit_busca_mapeia_filtros_oficiais() -> None:
    client = RecordingClient()

    resultado = buscar_produtos_agrofit(
        termo="mosca branca",
        cultura="Soja",
        praga="Mosca branca",
        ingrediente_ativo="beauveria",
        categoria="Inseticida Microbiológico",
        produto_biologico=True,
        pagina=2,
        client=client,
    )

    assert client.calls == [
        (
            "agrofit",
            "/search/produtos-formulados",
            {
                "q": "mosca branca",
                "cultura": "Soja",
                "praga_nome_comum": "Mosca branca",
                "ingrediente_ativo": "beauveria",
                "classe_categoria_agronomica": "Inseticida Microbiológico",
                "produto_biologico": True,
                "page": 2,
            },
        )
    ]
    assert resultado["api"] == "AGROFIT v1"
    assert "prescrição" in str(resultado["aviso"]).lower()


def test_agrofit_exige_filtro_para_evitar_consulta_ampla() -> None:
    with pytest.raises(ValueError, match="filtro"):
        buscar_produtos_agrofit(client=RecordingClient())


def test_agrofit_consulta_produto_por_registro() -> None:
    client = RecordingClient(data=[{"numero_registro": "5810"}])
    resultado = consultar_produto_agrofit("5810", client=client)

    assert client.calls == [("agrofit", "/produtos-formulados/5810", {})]
    assert resultado["resultados"] == [{"numero_registro": "5810"}]


def test_agritec_zarc_valida_risco_e_mapeia_parametros() -> None:
    client = RecordingClient()
    resultado = consultar_zarc_agritec(
        codigo_ibge=5105259,
        id_cultura=1209,
        client=client,
    )

    assert client.calls == [
        (
            "agritec",
            "/zoneamento",
            {"codigoIBGE": 5105259, "idCultura": 1209, "risco": "todos"},
        )
    ]
    assert resultado["api"] == "Agritec v2"

    with pytest.raises(ValueError, match="risco"):
        consultar_zarc_agritec(5105259, 1209, risco="50", client=client)


def test_agritec_cultivares_mapeia_filtros() -> None:
    client = RecordingClient()
    buscar_cultivares_agritec(
        id_cultura=1209,
        uf="mt",
        safra="2026-2027",
        grupo="II",
        cultivar="BRS",
        client=client,
    )

    assert client.calls == [
        (
            "agritec",
            "/cultivares",
            {
                "idCultura": 1209,
                "uf": "MT",
                "safra": "2026-2027",
                "grupo": "II",
                "cultivar": "BRS",
            },
        )
    ]


def test_agritec_resolve_municipio_e_cultura_sem_acentos() -> None:
    municipios = RecordingClient(
        data={
            "meta": {"totalCount": 2},
            "data": [
                {"codigoIBGE": 5105259, "nome": "LUCAS DO RIO VERDE", "uf": "MT"},
                {"codigoIBGE": 5107909, "nome": "SINOP", "uf": "MT"},
            ],
        }
    )
    culturas = RecordingClient(
        data={
            "meta": {"totalCount": 2},
            "data": [
                {"id": 1209, "nome": "SOJA SEQUEIRO"},
                {"id": 6060, "nome": "SOJA - NÍVEIS DE MANEJO"},
            ],
        }
    )

    resultado_municipio = buscar_municipios_agritec("lucas do rio verde", "mt", client=municipios)
    resultado_cultura = buscar_culturas_agritec("niveis de manejo", client=culturas)

    assert municipios.calls == [("agritec", "/municipios", {"uf": "MT"})]
    assert resultado_municipio["resultados"]["data"][0]["codigoIBGE"] == 5105259
    assert resultado_municipio["resultados"]["meta"]["limiteRetornado"] == 1
    assert culturas.calls == [("agritec", "/culturas", {})]
    assert resultado_cultura["resultados"]["data"][0]["id"] == 6060


@pytest.mark.parametrize(
    ("tipo", "esperado"),
    [
        ("biologico", "/search/produtos-biologicos"),
        ("inoculante", "/search/inoculantes"),
    ],
)
def test_bioinsumos_seleciona_endpoint(tipo: str, esperado: str) -> None:
    client = RecordingClient()
    buscar_produtos_bioinsumos(
        tipo=tipo,
        termo="soja",
        cultura="Soja",
        client=client,
    )

    assert client.calls[0][0] == "bioinsumos"
    assert client.calls[0][1] == esperado


def test_bioinsumos_rejeita_filtro_de_inoculante_em_produto_biologico() -> None:
    with pytest.raises(ValueError, match="exclusivos de inoculantes"):
        buscar_produtos_bioinsumos(
            tipo="biologico",
            termo="soja",
            uf="MT",
            client=RecordingClient(),
        )


def test_bioinsumos_rejeita_filtro_biologico_em_inoculante() -> None:
    with pytest.raises(ValueError, match="exclusivos de produtos biológicos"):
        buscar_produtos_bioinsumos(
            tipo="inoculante",
            termo="soja",
            praga="mosca branca",
            client=RecordingClient(),
        )


def test_agrotermos_busca_parcial_ou_relacoes() -> None:
    client = RecordingClient()
    parcial = buscar_termos_agrotermos("soj", client=client)
    relacoes = buscar_termos_agrotermos("soja", incluir_relacoes=True, client=client)

    assert client.calls == [
        ("agrotermos", "/termoParcial", {"label": "soj"}),
        ("agrotermos", "/termoComRelacoes", {"label": "soja"}),
    ]
    assert parcial["tipo_busca"] == "fragmento_sem_relacoes"
    assert relacoes["tipo_busca"] == "termo_exato_com_relacoes"
