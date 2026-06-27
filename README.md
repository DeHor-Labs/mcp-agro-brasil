# mcp-agro-brasil

MCP server de dados do agronegócio brasileiro: cotações de boi gordo, soja, milho e leite, calendário de safra (CONAB), previsão do tempo, câmbio PTAX, exportações agro e notícias do setor.

Parte da família [MCP Brasil](https://github.com/DeHor-Labs) junto com
[mcp-fiscal-brasil](https://github.com/DeHor-Labs/mcp-fiscal-brasil) e
[mcp-juridico-brasil](https://github.com/DeHor-Labs/mcp-juridico-brasil).

[![CI](https://github.com/DeHor-Labs/mcp-agro-brasil/actions/workflows/ci.yml/badge.svg)](https://github.com/DeHor-Labs/mcp-agro-brasil/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-agro-brasil?color=2e7d32&label=PyPI)](https://pypi.org/project/mcp-agro-brasil/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-2e7d32)](https://www.python.org/)
[![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-4caf50)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-compatível-7c3aed)](https://modelcontextprotocol.io)

---

## O que é

`mcp-agro-brasil` conecta qualquer cliente MCP (Claude Desktop, Claude Code, outros) a indicadores
do agronegócio brasileiro em tempo quase real:

- **Boi gordo** - cotação regional por praça via Scot Consultoria e indicador nacional ESALQ/B3
- **Soja** - indicador CEPEA/ESALQ Porto de Paranaguá (R$/saca 60 kg)
- **Milho** - indicador CEPEA/ESALQ (R$/saca 60 kg)
- **Leite** - preço ao produtor CEPEA por estado (R$/litro)
- **Clima** - previsão do tempo (máxima, mínima, chuva) para cidades brasileiras via Open-Meteo
- **Câmbio** - cotação PTAX oficial USD/BRL via Banco Central do Brasil
- **Exportações** - volume (kg/ton) e valor FOB (USD) exportado de soja, carne bovina e milho via Comex Stat / MDIC
- **Notícias** - últimas manchetes do agronegócio via RSS (Canal Rural), com filtro por tema
- **Calendário de safra** - janelas de plantio e colheita por cultura e região, curado do CONAB
- **Futuros B3** - informação sobre contratos BGI, CCM, SFI, ICF (fonte paga; alternativas indicadas)
- **Conversões** - arroba, saca, hectare, alqueire e outras unidades do agro

Os dados de cotação são obtidos por scraping de páginas públicas com cache local. Clima e câmbio usam APIs JSON abertas e gratuitas.

---

## Instalação rápida

A forma mais simples, sem instalação permanente:

```bash
uvx mcp-agro-brasil
```

Ou instale com pip/uv:

```bash
pip install mcp-agro-brasil
# ou
uv add mcp-agro-brasil
```

---

## Configuração MCP

### Claude Desktop

Adicione ao `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agro-brasil": {
      "command": "uvx",
      "args": ["mcp-agro-brasil"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add agro-brasil -- uvx mcp-agro-brasil
```

Ou adicione ao `.claude/settings.json` do projeto:

```json
{
  "mcpServers": {
    "agro-brasil": {
      "command": "uvx",
      "args": ["mcp-agro-brasil"]
    }
  }
}
```

---

## Ferramentas disponíveis

| Ferramenta | Descrição | Parâmetros |
|------------|-----------|------------|
| `cotacao_boi_gordo` | Cotação regional de boi gordo (Scot, fallback ESALQ) | `praca` (ex.: "GO Goiânia") |
| `indicador_esalq` | Indicador nacional ESALQ/B3 de boi gordo | - |
| `cotacao_soja` | Indicador CEPEA/ESALQ de soja - Porto de Paranaguá | - |
| `cotacao_milho` | Indicador CEPEA/ESALQ de milho | - |
| `cotacao_leite` | Preço ao produtor CEPEA de leite por estado | `estado` (ex.: "GO", "Brasil") |
| `clima_previsao` | Previsão do tempo para cidade brasileira (Open-Meteo) | `cidade` (ex.: "Goiânia"), `dias` (1-7) |
| `cambio_dolar` | Cotação PTAX oficial USD/BRL (Banco Central do Brasil) | - |
| `exportacao_agro` | Volume e valor FOB exportado via Comex Stat / MDIC | `produto` ("soja", "carne_bovina", "milho") |
| `noticias_agro` | Últimas notícias do agronegócio via RSS | `tema` (ex.: "soja"), `limite` (1-20) |
| `calendario_safra` | Calendário de plantio e colheita por cultura e região (CONAB) | `cultura` (ex.: "soja"), `regiao` (ex.: "GO", "Centro-Oeste") |
| `futuros_b3` | Futuros agrícolas B3 - informa disponibilidade (requer fonte paga) | `contrato` ("BGI", "CCM", "SFI", "ICF") |
| `converter` | Converte entre unidades do agro (peso e área) | `valor`, `de_unidade`, `para_unidade` |
| `listar_pracas` | Lista praças disponíveis no provider Scot | - |
| `listar_produtos` | Lista todos os produtos com cotação disponível | - |
| `listar_unidades` | Lista unidades suportadas pelo conversor | - |

### Exemplos de retorno

**`cotacao_boi_gordo("GO Goiânia")`**
```json
{
  "praca": "GO Goiânia",
  "a_vista": 312.50,
  "trinta_dias": 315.00,
  "unidade": "R$/@",
  "moeda": "BRL",
  "fonte": "Scot Consultoria",
  "data_consulta": "2026-06-27T10:00:00",
  "cache_hit": false
}
```

**`cotacao_soja()`**
```json
{
  "indicador": "Soja CEPEA/ESALQ - Paranaguá",
  "a_vista": 142.30,
  "unidade": "R$/saca 60 kg",
  "moeda": "BRL",
  "fonte": "CEPEA/ESALQ via Notícias Agrícolas",
  "data_consulta": "2026-06-27T10:00:00"
}
```

**`converter(50, "arroba", "kg")`**
```json
{
  "valor_original": 50.0,
  "de_unidade": "arroba",
  "resultado": 735.0,
  "para_unidade": "kg"
}
```

---

## Praças suportadas (boi gordo)

GO Goiânia, MS Campo Grande, MT Cuiabá, MG Belo Horizonte, SP Araçatuba,
SP Barretos, SP Presidente Prudente, SP São José do Rio Preto, PR Cascavel,
RS Porto Alegre, PA Redenção, BA Feira de Santana.

Para praças fora desta lista, o sistema usa fallback para o indicador nacional ESALQ/B3.

## Estados suportados (leite)

RS, SC, PR, SP, MG, GO, BA, RJ, ES e Brasil (média nacional).

---

## Fontes e atribuição

- **Scot Consultoria** - cotações regionais de boi gordo: [scotconsultoria.com.br](https://www.scotconsultoria.com.br/cotacoes/boi-gordo/)
- **ESALQ/B3 via Notícias Agrícolas** - indicador nacional boi gordo: [noticiasagricolas.com.br](https://www.noticiasagricolas.com.br/cotacoes/boi-gordo/boi-gordo-indicador-esalq-bmf)
- **CEPEA/ESALQ via Notícias Agrícolas** - soja, milho e leite: [noticiasagricolas.com.br](https://www.noticiasagricolas.com.br/cotacoes/)
- **Open-Meteo** - previsão do tempo: [open-meteo.com](https://open-meteo.com/) (API aberta, sem token)
- **Banco Central do Brasil (PTAX)** - câmbio USD/BRL: [olinda.bcb.gov.br](https://olinda.bcb.gov.br/) (API aberta, sem token)
- **Comex Stat / MDIC** - exportações do agronegócio: [comexstat.mdic.gov.br](https://comexstat.mdic.gov.br/) (API aberta, sem token)
- **Canal Rural** - notícias do agronegócio: [canalrural.com.br](https://www.canalrural.com.br/) (RSS público)

---

## Aviso legal

Os indicadores CEPEA/ESALQ (soja, milho, leite e boi gordo ESALQ/B3) são produzidos pela
**ESALQ-USP / CEPEA** e distribuídos sob licença **Creative Commons BY-NC** (não comercial,
com atribuição). Este projeto é de uso informativo e educacional, com atribuição completa
da fonte em todas as respostas.

**Para uso comercial ou redistribuição em produto pago**, obtenha licença junto ao
CEPEA ([cepea.esalq.usp.br](https://www.cepea.esalq.usp.br)) ou um provedor licenciado
(ex.: Agrolink, Notícias Agrícolas via contrato).

O scraping respeita as fontes: cache local de 15 minutos, sem sobrecarga de requisições.

---

## Roadmap

**Entregue**
- [x] Boi gordo - cotação regional (Scot Consultoria) + indicador nacional (ESALQ/B3)
- [x] Soja - indicador CEPEA/ESALQ Porto de Paranaguá
- [x] Milho - indicador CEPEA/ESALQ
- [x] Leite - preço ao produtor CEPEA por estado
- [x] Conversões de unidades (arroba, saca, hectare, alqueire, tonelada...)
- [x] Clima - previsão do tempo por cidade via Open-Meteo
- [x] Câmbio USD/BRL PTAX via Banco Central do Brasil
- [x] Exportações do agronegócio via Comex Stat / MDIC (soja, carne bovina, milho)
- [x] Notícias do agronegócio via RSS (Canal Rural)

**Onda 3 - Safra e Mercado Futuro**
- [x] Calendário de safra via CONAB (soja, milho 1a/2a, feijão, café, sorgo, algodão - 5 regiões)
- [x] Futuros B3 (BGI, CCM, SFI, ICF) - tool implementada; fonte paga não integrada (brapi.dev Pro / Cedro)

**Próximos**
- [ ] Integrar futuros B3 quando fonte gratuita ou open-access estiver disponível

---

## Desenvolvimento

```bash
git clone https://github.com/DeHor-Labs/mcp-agro-brasil.git
cd mcp-agro-brasil

# Instalar com uv
uv sync --extra dev

# Rodar testes
uv run pytest

# Lint
uv run ruff check .
uv run ruff format .
```

---

## Licença

MIT - ver [LICENSE](LICENSE).

Desenvolvido por [Nikolas de Hor](https://github.com/nikolasdehor) - nikolasdehor79@gmail.com
