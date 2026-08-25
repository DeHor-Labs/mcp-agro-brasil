"""Cliente e consultas para as APIs oficiais AgroAPI da Embrapa.

As APIs usam OAuth 2.0 no fluxo ``client_credentials``. A integração é opcional
e lê as credenciais apenas das variáveis de ambiente ``AGROAPI_CLIENT_ID`` e
``AGROAPI_CLIENT_SECRET``. Também é possível fornecer um token já emitido em
``AGROAPI_TOKEN``.

Documentação oficial: https://www.portal.agroapi.cnptia.embrapa.br/
"""

from __future__ import annotations

import os
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import date
from threading import Lock
from typing import Any, Literal, Protocol
from urllib.parse import quote

import httpx

ApiName = Literal["agrofit", "agritec", "bioinsumos", "agrotermos"]
ParamValue = str | int | bool

_TOKEN_URL = "https://api.cnptia.embrapa.br/token"
_API_BASE_URLS: dict[ApiName, str] = {
    "agrofit": "https://api.cnptia.embrapa.br/agrofit/v1",
    "agritec": "https://api.cnptia.embrapa.br/agritec/v2",
    "bioinsumos": "https://api.cnptia.embrapa.br/bioinsumos/v2",
    "agrotermos": "https://api.cnptia.embrapa.br/agrotermos/v1",
}
_API_LABELS: dict[ApiName, str] = {
    "agrofit": "AGROFIT v1",
    "agritec": "Agritec v2",
    "bioinsumos": "Bioinsumos v2",
    "agrotermos": "AgroTermos v1",
}
_DOC_URLS: dict[ApiName, str] = {
    "agrofit": "https://www.portal.agroapi.cnptia.embrapa.br/api-docs/agrofit",
    "agritec": "https://www.portal.agroapi.cnptia.embrapa.br/api-docs/agritec",
    "bioinsumos": "https://www.portal.agroapi.cnptia.embrapa.br/api-docs/bioinsumos",
    "agrotermos": "https://www.portal.agroapi.cnptia.embrapa.br/api-docs/agrotermos",
}
_TIMEOUT = 20.0
_TOKEN_EXPIRY_MARGIN_SECONDS = 30

_AGROFIT_AVISO = (
    "Consulta informativa a registros oficiais. O resultado não constitui prescrição agronômica. "
    "Confirme registro vigente, cultura, alvo, bula e receituário com profissional habilitado."
)
_BIOINSUMOS_AVISO = (
    "Consulta informativa a registros oficiais. Confirme registro vigente, indicação de uso, "
    "rótulo/bula e orientação de profissional habilitado antes da aplicação."
)
_ZARC_AVISO = (
    "O ZARC informa janelas oficiais de menor risco climático; não garante produtividade, "
    "seguro ou crédito e não substitui assistência técnica."
)
_UFS = {
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
}


class AgroApiCredentialsError(RuntimeError):
    """Indica que a integração AgroAPI não recebeu credenciais suficientes."""


@dataclass(frozen=True)
class AgroApiResponse:
    """Resposta normalizada do gateway AgroAPI."""

    data: Any
    pagination: dict[str, int]


class AgroApiTransport(Protocol):
    """Contrato mínimo usado pelas consultas de domínio e pelos testes."""

    def get(
        self,
        api: ApiName,
        path: str,
        params: dict[str, ParamValue] | None = None,
    ) -> AgroApiResponse: ...


class AgroApiClient:
    """Cliente HTTP autenticado para o gateway AgroAPI da Embrapa."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        access_token: str | None = None,
        timeout: float = _TIMEOUT,
    ) -> None:
        self._client_id = client_id.strip() if client_id else None
        self._client_secret = client_secret.strip() if client_secret else None
        self._static_token = access_token.strip() if access_token else None
        self._timeout = timeout
        self._cached_token: str | None = None
        self._token_expires_at = 0.0
        self._token_generation = 0
        self._token_lock = Lock()

    @classmethod
    def from_env(cls) -> AgroApiClient:
        """Cria cliente usando somente as variáveis de ambiente documentadas."""
        return cls(
            client_id=_first_env("AGROAPI_CLIENT_ID", "AGROAPI_CONSUMER_KEY"),
            client_secret=_first_env("AGROAPI_CLIENT_SECRET", "AGROAPI_CONSUMER_SECRET"),
            access_token=_first_env("AGROAPI_TOKEN", "AGROAPI_ACCESS_TOKEN"),
        )

    def _access_token(self) -> tuple[str, int]:
        if self._static_token:
            return self._static_token, 0

        with self._token_lock:
            agora = time.monotonic()
            if self._cached_token and agora < self._token_expires_at:
                return self._cached_token, self._token_generation

            if not self._client_id or not self._client_secret:
                raise AgroApiCredentialsError(
                    "AgroAPI não configurada. Defina AGROAPI_CLIENT_ID e "
                    "AGROAPI_CLIENT_SECRET, ou forneça AGROAPI_TOKEN."
                )

            try:
                with httpx.Client(
                    timeout=self._timeout,
                    auth=(self._client_id, self._client_secret),
                    follow_redirects=False,
                ) as client:
                    response = client.post(
                        _TOKEN_URL,
                        data={"grant_type": "client_credentials"},
                        headers={"Accept": "application/json"},
                    )
                    response.raise_for_status()
                    payload = response.json()
            except httpx.HTTPStatusError as exc:
                raise AgroApiCredentialsError(
                    f"Falha ao autenticar na AgroAPI (HTTP {exc.response.status_code}). "
                    "Confirme a assinatura das APIs e as credenciais da aplicação."
                ) from exc
            except httpx.HTTPError as exc:
                raise RuntimeError(f"Falha de rede ao autenticar na AgroAPI: {exc}") from exc

            token = payload.get("access_token") if isinstance(payload, dict) else None
            if not isinstance(token, str) or not token.strip():
                raise AgroApiCredentialsError("A AgroAPI não retornou um access_token válido.")

            expires_in_raw = payload.get("expires_in", 3600)
            try:
                expires_in = max(int(expires_in_raw), 1)
            except (TypeError, ValueError):
                expires_in = 3600

            self._cached_token = token.strip()
            self._token_generation += 1
            margem = min(_TOKEN_EXPIRY_MARGIN_SECONDS, max(expires_in // 10, 1))
            self._token_expires_at = agora + max(expires_in - margem, 1)
            return self._cached_token, self._token_generation

    def _invalidate_cached_token(self, rejected_generation: int) -> None:
        """Invalida somente o token que foi efetivamente rejeitado.

        A comparação da geração sob o mesmo lock impede que uma resposta 401
        atrasada apague um token que outra chamada concorrente acabou de
        renovar, mesmo se o emissor repetir o mesmo valor textual do token.
        """
        with self._token_lock:
            if self._cached_token is not None and self._token_generation == rejected_generation:
                self._cached_token = None
                self._token_expires_at = 0.0

    def _request(
        self,
        api: ApiName,
        path: str,
        params: dict[str, ParamValue],
        *,
        allow_refresh: bool,
    ) -> httpx.Response:
        token, token_generation = self._access_token()
        url = f"{_API_BASE_URLS[api]}{path}"
        try:
            with httpx.Client(timeout=self._timeout, follow_redirects=False) as client:
                response = client.get(
                    url,
                    params=params,
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {token}",
                    },
                )
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Falha de rede ao consultar {_API_LABELS[api]}: {exc}") from exc

        if response.status_code == 401 and allow_refresh and not self._static_token:
            self._invalidate_cached_token(token_generation)
            return self._request(api, path, params, allow_refresh=False)

        if response.status_code == 401:
            raise AgroApiCredentialsError(
                f"Token rejeitado por {_API_LABELS[api]}. Renove as credenciais ou o AGROAPI_TOKEN."
            )

        response.raise_for_status()
        return response

    def get(
        self,
        api: ApiName,
        path: str,
        params: dict[str, ParamValue] | None = None,
    ) -> AgroApiResponse:
        """Executa GET autenticado e preserva metadados de paginação."""
        response = self._request(api, path, params or {}, allow_refresh=True)
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(f"{_API_LABELS[api]} retornou resposta JSON inválida.") from exc

        pagination: dict[str, int] = {}
        header_map = {
            "X-Records-Count": "total_registros",
            "X-Pages": "total_paginas",
            "X-Page-Size": "tamanho_pagina",
        }
        for header, key in header_map.items():
            value = response.headers.get(header)
            if value is not None:
                try:
                    pagination[key] = int(value)
                except ValueError:
                    continue

        page = (params or {}).get("page")
        if isinstance(page, int):
            pagination["pagina"] = page
        return AgroApiResponse(data=data, pagination=pagination)


_DEFAULT_CLIENT: AgroApiClient | None = None


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value
    return None


def is_configured() -> bool:
    """Indica se há token ou par completo de credenciais no ambiente."""
    if _first_env("AGROAPI_TOKEN", "AGROAPI_ACCESS_TOKEN"):
        return True
    client_id = _first_env("AGROAPI_CLIENT_ID", "AGROAPI_CONSUMER_KEY")
    client_secret = _first_env("AGROAPI_CLIENT_SECRET", "AGROAPI_CONSUMER_SECRET")
    return bool(client_id and client_secret)


def _client(client: AgroApiTransport | None) -> AgroApiTransport:
    global _DEFAULT_CLIENT
    if client is not None:
        return client
    if _DEFAULT_CLIENT is None:
        _DEFAULT_CLIENT = AgroApiClient.from_env()
    return _DEFAULT_CLIENT


def _texto(value: str) -> str:
    return value.strip()


def _pagina(value: int) -> int:
    if value < 1:
        raise ValueError("pagina deve ser maior ou igual a 1.")
    return value


def _resultado(
    api: ApiName,
    response: AgroApiResponse,
    *,
    aviso: str | None = None,
) -> dict[str, Any]:
    resultado: dict[str, Any] = {
        "fonte": "Embrapa Agricultura Digital - AgroAPI",
        "fonte_url": _DOC_URLS[api],
        "api": _API_LABELS[api],
        "resultados": response.data,
        "data_consulta": date.today().isoformat(),
    }
    if response.pagination:
        resultado["paginacao"] = response.pagination
    if aviso:
        resultado["aviso"] = aviso
    return resultado


def _resumo_produtos(data: Any) -> Any:
    """Remove documentos extensos das buscas e mantém os campos de decisão."""
    if not isinstance(data, list):
        return data
    campos = (
        "numero_registro",
        "marca_comercial",
        "titular_registro",
        "produto_biologico",
        "classe_categoria_agronomica",
        "formulacao",
        "ingrediente_ativo",
        "modo_acao",
        "tecnica_aplicacao",
        "classificacao_toxicologica",
        "classificacao_ambiental",
        "produto_agricultura_organica",
        "url_agrofit",
    )
    produtos: list[Any] = []
    for item in data:
        if not isinstance(item, dict):
            produtos.append(item)
            continue
        resumo = {key: item[key] for key in campos if key in item}
        indicacoes = item.get("indicacao_uso")
        if isinstance(indicacoes, list):
            resumo["indicacoes_uso_total"] = len(indicacoes)
        documentos = item.get("documento_cadastrado")
        if isinstance(documentos, list):
            resumo["documentos_total"] = len(documentos)
        produtos.append(resumo)
    return produtos


def _normalizar_busca(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def _filtrar_envelope(data: Any, campo: str, termo: str, limite: int = 20) -> Any:
    if not isinstance(data, dict) or not isinstance(data.get("data"), list):
        return data
    termo_normalizado = _normalizar_busca(termo)
    encontrados = [
        item
        for item in data["data"]
        if isinstance(item, dict)
        and termo_normalizado in _normalizar_busca(str(item.get(campo, "")))
    ]
    return {
        "meta": {
            "totalCount": len(encontrados),
            "totalCountFonte": data.get("meta", {}).get("totalCount")
            if isinstance(data.get("meta"), dict)
            else None,
            "limiteRetornado": len(encontrados[:limite]),
        },
        "data": encontrados[:limite],
    }


def buscar_produtos_agrofit(
    termo: str = "",
    cultura: str = "",
    praga: str = "",
    ingrediente_ativo: str = "",
    categoria: str = "",
    produto_biologico: bool | None = None,
    pagina: int = 1,
    *,
    client: AgroApiTransport | None = None,
) -> dict[str, Any]:
    """Busca produtos formulados registrados na API AGROFIT."""
    filtros: dict[str, ParamValue] = {
        "q": _texto(termo),
        "cultura": _texto(cultura),
        "praga_nome_comum": _texto(praga),
        "ingrediente_ativo": _texto(ingrediente_ativo),
        "classe_categoria_agronomica": _texto(categoria),
    }
    filtros = {key: value for key, value in filtros.items() if value != ""}
    if produto_biologico is not None:
        filtros["produto_biologico"] = produto_biologico
    if not filtros:
        raise ValueError("Informe ao menos um filtro para pesquisar produtos no AGROFIT.")
    filtros["page"] = _pagina(pagina)

    response = _client(client).get("agrofit", "/search/produtos-formulados", filtros)
    response = AgroApiResponse(
        data=_resumo_produtos(response.data),
        pagination=response.pagination,
    )
    return _resultado("agrofit", response, aviso=_AGROFIT_AVISO)


def consultar_produto_agrofit(
    numero_registro: str,
    *,
    client: AgroApiTransport | None = None,
) -> dict[str, Any]:
    """Consulta o detalhe de um produto AGROFIT por número de registro."""
    registro = _texto(numero_registro)
    if not registro:
        raise ValueError("numero_registro não pode ser vazio.")
    path = f"/produtos-formulados/{quote(registro, safe='')}"
    response = _client(client).get("agrofit", path)
    return _resultado("agrofit", response, aviso=_AGROFIT_AVISO)


def buscar_municipios_agritec(
    nome: str,
    uf: str,
    *,
    client: AgroApiTransport | None = None,
) -> dict[str, Any]:
    """Resolve nome e UF para o código IBGE usado pela Agritec."""
    nome_normalizado = _texto(nome)
    if not nome_normalizado:
        raise ValueError("nome não pode ser vazio.")
    uf_normalizada = _texto(uf).upper()
    if uf_normalizada not in _UFS:
        raise ValueError("uf deve ser uma sigla válida de unidade federativa brasileira.")
    response = _client(client).get("agritec", "/municipios", {"uf": uf_normalizada})
    response = AgroApiResponse(
        data=_filtrar_envelope(response.data, "nome", nome_normalizado),
        pagination=response.pagination,
    )
    return _resultado("agritec", response)


def buscar_culturas_agritec(
    nome: str,
    *,
    client: AgroApiTransport | None = None,
) -> dict[str, Any]:
    """Resolve nome de cultura para o identificador usado pela Agritec."""
    nome_normalizado = _texto(nome)
    if not nome_normalizado:
        raise ValueError("nome não pode ser vazio.")
    response = _client(client).get("agritec", "/culturas")
    response = AgroApiResponse(
        data=_filtrar_envelope(response.data, "nome", nome_normalizado),
        pagination=response.pagination,
    )
    return _resultado("agritec", response)


def consultar_zarc_agritec(
    codigo_ibge: int,
    id_cultura: int,
    risco: str = "20",
    *,
    client: AgroApiTransport | None = None,
) -> dict[str, Any]:
    """Consulta o Zoneamento Agrícola de Risco Climático na Agritec v2."""
    if codigo_ibge <= 0:
        raise ValueError("codigo_ibge deve ser um inteiro positivo.")
    if id_cultura <= 0:
        raise ValueError("id_cultura deve ser um inteiro positivo.")
    risco_normalizado = _texto(risco).lower()
    if risco_normalizado not in {"20", "30", "40", "todos"}:
        raise ValueError("risco deve ser 20, 30, 40 ou 'todos'.")

    response = _client(client).get(
        "agritec",
        "/zoneamento",
        {
            "codigoIBGE": codigo_ibge,
            "idCultura": id_cultura,
            "risco": risco_normalizado,
        },
    )
    return _resultado("agritec", response, aviso=_ZARC_AVISO)


def buscar_cultivares_agritec(
    id_cultura: int,
    uf: str,
    safra: str = "2026-2027",
    regiao: str = "",
    grupo: str = "",
    cultivar: str = "",
    *,
    client: AgroApiTransport | None = None,
) -> dict[str, Any]:
    """Busca cultivares indicadas pela Agritec para cultura, UF e safra."""
    if id_cultura <= 0:
        raise ValueError("id_cultura deve ser um inteiro positivo.")
    uf_normalizada = _texto(uf).upper()
    if uf_normalizada not in _UFS:
        raise ValueError("uf deve ser uma sigla válida de unidade federativa brasileira.")
    safra_normalizada = _texto(safra)
    if not re.fullmatch(r"\d{4}-\d{4}", safra_normalizada):
        raise ValueError("safra deve usar o formato YYYY-YYYY, por exemplo 2026-2027.")

    params: dict[str, ParamValue] = {
        "idCultura": id_cultura,
        "uf": uf_normalizada,
        "safra": safra_normalizada,
    }
    regiao_normalizada = _texto(regiao)
    if regiao_normalizada:
        if regiao_normalizada not in {"1", "2", "3", "4", "5"}:
            raise ValueError("regiao deve estar entre 1 e 5.")
        params["regiao"] = regiao_normalizada
    grupo_normalizado = _texto(grupo).upper()
    if grupo_normalizado:
        if grupo_normalizado not in {"I", "II", "III", "IV"}:
            raise ValueError("grupo deve ser I, II, III ou IV.")
        params["grupo"] = grupo_normalizado
    cultivar_normalizada = _texto(cultivar)
    if cultivar_normalizada:
        params["cultivar"] = cultivar_normalizada

    response = _client(client).get("agritec", "/cultivares", params)
    return _resultado("agritec", response, aviso=_ZARC_AVISO)


def buscar_produtos_bioinsumos(
    tipo: str = "biologico",
    termo: str = "",
    cultura: str = "",
    praga: str = "",
    ingrediente_ativo: str = "",
    uf: str = "",
    especie: str = "",
    pagina: int = 1,
    *,
    client: AgroApiTransport | None = None,
) -> dict[str, Any]:
    """Busca produtos biológicos ou inoculantes registrados no MAPA."""
    tipo_normalizado = _texto(tipo).lower().replace("-", "_")
    aliases = {
        "biologico": "biologico",
        "biologicos": "biologico",
        "produto_biologico": "biologico",
        "produtos_biologicos": "biologico",
        "inoculante": "inoculante",
        "inoculantes": "inoculante",
    }
    categoria = aliases.get(tipo_normalizado)
    if categoria is None:
        raise ValueError("tipo deve ser 'biologico' ou 'inoculante'.")

    params: dict[str, ParamValue] = {
        "q": _texto(termo),
        "cultura": _texto(cultura),
    }
    path = "/search/produtos-biologicos"
    if categoria == "biologico":
        params.update(
            {
                "praga_nome_comum": _texto(praga),
                "ingrediente_ativo": _texto(ingrediente_ativo),
            }
        )
        if _texto(uf) or _texto(especie):
            raise ValueError("uf e especie são filtros exclusivos de inoculantes.")
    else:
        path = "/search/inoculantes"
        uf_normalizada = _texto(uf).upper()
        if uf_normalizada:
            if uf_normalizada not in _UFS:
                raise ValueError("uf deve ser uma sigla válida de unidade federativa brasileira.")
            params["uf"] = uf_normalizada
        especie_normalizada = _texto(especie)
        if especie_normalizada:
            params["especie"] = especie_normalizada
        if _texto(praga) or _texto(ingrediente_ativo):
            raise ValueError(
                "praga e ingrediente_ativo são filtros exclusivos de produtos biológicos."
            )

    params = {key: value for key, value in params.items() if value != ""}
    if not params:
        raise ValueError("Informe ao menos um filtro para pesquisar bioinsumos.")
    params["page"] = _pagina(pagina)

    response = _client(client).get("bioinsumos", path, params)
    if categoria == "biologico":
        response = AgroApiResponse(
            data=_resumo_produtos(response.data),
            pagination=response.pagination,
        )
    resultado = _resultado("bioinsumos", response, aviso=_BIOINSUMOS_AVISO)
    resultado["tipo_consulta"] = categoria
    return resultado


def buscar_termos_agrotermos(
    termo: str,
    incluir_relacoes: bool = False,
    *,
    client: AgroApiTransport | None = None,
) -> dict[str, Any]:
    """Busca fragmento ou, opcionalmente, relações de um termo exato no AgroTermos."""
    termo_normalizado = _texto(termo)
    if not termo_normalizado:
        raise ValueError("termo não pode ser vazio.")
    path = "/termoComRelacoes" if incluir_relacoes else "/termoParcial"
    response = _client(client).get("agrotermos", path, {"label": termo_normalizado})
    resultado = _resultado("agrotermos", response)
    resultado["tipo_busca"] = (
        "termo_exato_com_relacoes" if incluir_relacoes else "fragmento_sem_relacoes"
    )
    return resultado
