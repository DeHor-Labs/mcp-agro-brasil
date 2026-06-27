# mcp-agro-brasil

MCP server de dados do agronegócio brasileiro para Claude e outros clientes MCP.

Terceiro da família [MCP Brasil](https://github.com/DeHor-Labs): após [mcp-fiscal-brasil](https://github.com/DeHor-Labs/mcp-fiscal-brasil) e [mcp-juridico-brasil](https://github.com/DeHor-Labs/mcp-juridico-brasil).

## Instalação

```bash
pip install mcp-agro-brasil
```

Ou com uv:

```bash
uv add mcp-agro-brasil
```

## Configuração MCP

Adicione ao seu `claude_desktop_config.json` (ou equivalente):

```json
{
  "mcpServers": {
    "agro-brasil": {
      "command": "mcp-agro-brasil"
    }
  }
}
```

## Tools disponíveis

| Tool | Descrição |
|------|-----------|
| `cotacao_boi_gordo` | Cotação regional de boi gordo (Scot Consultoria, fallback ESALQ) |
| `indicador_esalq` | Indicador nacional ESALQ/B3 de boi gordo |
| `converter` | Converte entre unidades do agro (arroba, saca, ha, alqueire...) |
| `listar_pracas` | Lista praças disponíveis no provider Scot |
| `listar_unidades` | Lista unidades suportadas pelo conversor |

## Exemplos de uso

**Cotação de boi gordo em Goiânia:**
```
Qual a cotação do boi gordo em Goiânia hoje?
```

**Cotação em outra praça:**
```
Qual o preço do boi gordo em Araçatuba?
```

**Indicador nacional:**
```
Qual o indicador ESALQ/B3 do boi gordo agora?
```

**Conversão de unidades:**
```
Quanto vale 50 arrobas em quilogramas?
Converta 200 hectares para alqueires goianos.
1 saca de soja quantos quilos tem?
```

## Praças suportadas

GO Goiânia, MS Campo Grande, MT Cuiabá, MG Belo Horizonte, SP Araçatuba,
SP Barretos, SP Presidente Prudente, SP São José do Rio Preto, PR Cascavel,
RS Porto Alegre, PA Redenção, BA Feira de Santana.

## Fontes e atribuição

- **Scot Consultoria** - cotações regionais de boi gordo: [scotconsultoria.com.br](https://www.scotconsultoria.com.br/cotacoes/boi-gordo/)
- **ESALQ/B3 via Notícias Agrícolas** - indicador nacional: [noticiasagricolas.com.br](https://www.noticiasagricolas.com.br/cotacoes/boi-gordo/boi-gordo-indicador-esalq-bmf)

Os dados são obtidos por scraping de páginas públicas. Podem ter defasagem de minutos a horas em relação ao mercado em tempo real. Não use para decisões financeiras sem confirmar nas fontes originais.

## Roadmap

- [x] Boi gordo - cotação regional (Scot) + indicador nacional (ESALQ/B3)
- [x] Conversão de unidades (arroba, saca, hectare, alqueire...)
- [ ] Soja - cotação por praça e CBOT
- [ ] Milho - cotação regional e CBOT
- [ ] Café - indicador ESALQ e NY
- [ ] Leite - indicador CEPEA
- [ ] Câmbio USD/BRL (impacto nas commodities)
- [ ] Exportações - dados MDIC
- [ ] Safra - estimativas CONAB
- [ ] Notícias do agro

## Desenvolvimento

```bash
# Instalar dependências de desenvolvimento
pip install -e ".[dev]"

# Rodar testes
pytest

# Lint e formatação
ruff check .
ruff format .
```

## Licença

MIT - ver [LICENSE](LICENSE).
