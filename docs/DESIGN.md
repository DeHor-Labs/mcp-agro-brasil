# Design e Arquitetura - mcp-agro-brasil

## Visão geral

`mcp-agro-brasil` é um MCP server Python que expõe dados do agronegócio brasileiro
para assistentes de IA (Claude, etc.). Segue a mesma família de design de
`mcp-fiscal-brasil` e `mcp-juridico-brasil`.

## Separação core / providers / server

```
src/mcp_agro_brasil/
├── providers/       # fontes de dados (scraping, APIs)
│   ├── scot.py      # Scot Consultoria - cotação regional boi gordo (HTML)
│   └── esalq.py     # ESALQ/B3 via Notícias Agrícolas - indicador nacional
├── core/            # lógica de negócio independente de interface
│   ├── cotacao.py   # orquestração: primário Scot -> fallback ESALQ, cache
│   └── conversao.py # conversões puras de unidades (sem rede)
└── server.py        # tools FastMCP que expõem o core via MCP
```

**Por que separar core de server?**

- O core pode ser importado por outros projetos (ex.: AgroVoz) sem depender do MCP.
- Testes do core não precisam subir o servidor MCP.
- Novos providers (soja, milho) se plugam no core sem alterar a interface MCP.

## Estratégia de dados

### Cotação de boi gordo

1. Provider primário: `scot.py` - scraping do HTML da Scot Consultoria.
   - Extração por regex robusta (tolera atributos extras nos `<td>`).
   - Retorna à vista e 30 dias por praça.
2. Fallback: `esalq.py` - scraping do indicador nacional ESALQ/B3.
   - Ativado quando a praça não é encontrada na Scot ou em caso de erro de rede.
3. Nunca inventa valor: se ambos falharem, `RuntimeError` com mensagem clara.

### Cache em memória

- TTL de 4 horas por chave (praça ou indicador).
- Evita múltiplas requisições HTTP durante uma sessão Claude.
- Não persiste entre reinicializações do servidor.

### Conversão de unidades

- Puramente matemático, sem rede.
- Unidade canônica intermediária: `kg` (peso) e `m²` (área).
- Conversão cruzada peso-área é proibida e levanta `ValueError`.

## Extensibilidade

Para adicionar soja/milho/café/leite:

1. Criar `providers/cepea.py` (ou equivalente) com a função de busca.
2. Adicionar lógica de orquestração em `core/cotacao_graos.py`.
3. Registrar nova tool em `server.py` via `@app.tool()`.

Para conectar ao AgroVoz:

- Importar `mcp_agro_brasil.core.cotacao` diretamente no backend AgroVoz.
- O core não tem dependência do FastMCP, apenas de `httpx` e `pydantic`.

## Decisões técnicas

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| HTTP client | `httpx` | consistência com mcp-fiscal e mcp-juridico |
| Parsing | `re` (regex) | HTML simples, sem necessidade de BeautifulSoup |
| Cache | dict em memória | MVP; suficiente para sessão single-process |
| Build | hatchling | consistência com família MCP Brasil |
| Testes | pytest + fixtures HTML | evita dependência de rede nos testes |
