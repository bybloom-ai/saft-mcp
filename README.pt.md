<div align="center">

# SAF-T MCP Server

**Analise ficheiros SAF-T portugueses com assistentes de IA**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![SAF-T PT 1.04_01](https://img.shields.io/badge/SAF--T%20PT-1.04__01-green?style=flat-square)](https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/SAFT_PT/Paginas/news-saf-t-702.aspx)

[Instalacao](#instalacao) &#183; [Ferramentas](#ferramentas-disponiveis) &#183; [Configuracao](#configuracao)

*[English version](README.md)*

</div>

---

Um servidor **Model Context Protocol (MCP)** que permite a assistentes de IA como Claude, Cursor e Windsurf carregar, validar e analisar ficheiros [SAF-T](https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/SAFT_PT/Paginas/default.aspx) (Standard Audit File for Tax Purposes) portugueses. Carregue um ficheiro SAF-T e consulte faturas, obtenha resumos de faturacao, analises de IVA e valide a conformidade com as regras fiscais portuguesas.

### O que e o SAF-T PT?

O SAF-T PT e um ficheiro XML obrigatorio que todas as empresas portuguesas devem conseguir exportar do seu software de contabilidade/faturacao. Contem as faturas, pagamentos, clientes, produtos, registos de impostos e mais. Este servidor MCP transforma esse XML numa fonte de dados consultavel por assistentes de IA.

---

## Instalacao

### Pre-requisitos

- **Python 3.11+** e [uv](https://docs.astral.sh/uv/) (recomendado) ou pip
- Um **ficheiro SAF-T PT XML** exportado de qualquer software de faturacao/contabilidade portugues (PHC, Sage, Primavera, etc.)

### 1. Clonar e instalar

```bash
git clone https://github.com/bybloom-ai/saft-mcp.git
cd saft-mcp
uv sync
```

### 2. Adicionar ao assistente de IA

<details open>
<summary><strong>Claude Code</strong></summary>

```bash
claude mcp add saft-mcp -- /caminho/para/saft-mcp/.venv/bin/python -m saft_mcp
```
</details>

<details>
<summary><strong>Claude Desktop</strong></summary>

Adicionar a `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) ou `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "saft-mcp": {
      "command": "/caminho/para/saft-mcp/.venv/bin/python",
      "args": ["-m", "saft_mcp"]
    }
  }
}
```
</details>

<details>
<summary><strong>Cursor / VS Code / Outros clientes MCP</strong></summary>

Adicionar a configuracao do cliente MCP:

```json
{
  "mcpServers": {
    "saft-mcp": {
      "command": "/caminho/para/saft-mcp/.venv/bin/python",
      "args": ["-m", "saft_mcp"]
    }
  }
}
```
</details>

### 3. Comecar a usar

Pergunte ao assistente de IA:

> "Carrega o meu ficheiro SAF-T em ~/Documents/saft_2025.xml e da-me um resumo da faturacao"

O servidor analisa o ficheiro, extrai todas as faturas e dados fiscais, e disponibiliza-os para consulta em linguagem natural.

---

## Ferramentas Disponiveis

### `saft_load`

Carrega e analisa um ficheiro SAF-T PT XML. Deve ser chamado primeiro, antes de qualquer outra ferramenta.

| Parametro | Tipo | Descricao |
|-----------|------|-----------|
| `file_path` | string | Caminho para o ficheiro SAF-T XML |

Devolve nome da empresa, NIF, periodo fiscal, versao SAF-T e contagens de registos (clientes, produtos, faturas, pagamentos).

Suporta encodings Windows-1252 e UTF-8, stripping de BOM e detecao automatica de namespace. Ficheiros ate 50 MB sao analisados com DOM completo; ficheiros maiores usam streaming.

---

### `saft_validate`

Valida o ficheiro carregado contra o schema XSD oficial e regras de negocio portuguesas.

| Parametro | Tipo | Default | Descricao |
|-----------|------|---------|-----------|
| `rules` | list[string] | todas | Regras especificas a verificar |

Regras disponiveis:

| Regra | O que valida |
|-------|-------------|
| `xsd` | Estrutura XML contra o schema XSD SAF-T PT 1.04_01 |
| `numbering` | Numeracao sequencial de faturas dentro de cada serie |
| `nif` | Digito de controlo mod-11 do NIF |
| `tax_codes` | Taxas de imposto correspondem as taxas de IVA portuguesas |
| `atcud` | Codigos ATCUD presentes e bem formados |
| `hash_chain` | Continuidade de hash entre sequencias de faturas |
| `control_totals` | Totais calculados correspondem aos totais de controlo declarados |

Devolve resultados com severidade (erro/aviso), localizacao e sugestoes de correcao.

---

### `saft_summary`

Gera um resumo executivo do ficheiro carregado. Sem parametros.

Devolve:
- Totais de faturacao (bruto, notas de credito, liquido)
- Contagem de faturas e notas de credito
- Distribuicao de IVA por taxa
- Top 10 clientes por faturacao
- Distribuicao por tipo de documento (FT, FR, NC, ND, FS)

---

### `saft_query_invoices`

Pesquisa e filtra faturas com paginacao.

| Parametro | Tipo | Default | Descricao |
|-----------|------|---------|-----------|
| `date_from` | string | - | Data inicio (YYYY-MM-DD) |
| `date_to` | string | - | Data fim (YYYY-MM-DD) |
| `customer_nif` | string | - | Filtrar por NIF (correspondencia parcial) |
| `customer_name` | string | - | Filtrar por nome (case-insensitive, parcial) |
| `doc_type` | string | - | FT, FR, NC, ND ou FS |
| `min_amount` | number | - | Total bruto minimo |
| `max_amount` | number | - | Total bruto maximo |
| `status` | string | - | N (normal), A (anulada), F (faturada) |
| `limit` | integer | 50 | Resultados por pagina (max 500) |
| `offset` | integer | 0 | Offset de paginacao |

Devolve faturas com numero de documento, data, tipo, cliente, valores, estado e numero de linhas.

---

### `saft_tax_summary`

Gera uma analise de IVA agrupada por taxa, mes ou tipo de documento.

| Parametro | Tipo | Default | Descricao |
|-----------|------|---------|-----------|
| `date_from` | string | - | Data inicio (YYYY-MM-DD) |
| `date_to` | string | - | Data fim (YYYY-MM-DD) |
| `group_by` | string | `rate` | Agrupar por `rate` (taxa), `month` (mes) ou `doc_type` (tipo doc.) |

Devolve base tributavel, valor de IVA e total bruto por grupo, mais totais globais.

---

## Fluxo Tipico

```
1. saft_load       -> Carregar e analisar o ficheiro XML
2. saft_validate   -> Verificar conformidade (XSD + regras de negocio)
3. saft_summary    -> Visao geral (faturacao, top clientes, IVA)
4. saft_query_invoices -> Consultar faturas especificas
5. saft_tax_summary    -> Analise de IVA por taxa, mes ou tipo
```

Exemplos de perguntas apos carregar um ficheiro:

- "Qual foi a faturacao total da empresa este ano?"
- "Mostra-me todas as notas de credito acima de 500 euros"
- "Qual e a distribuicao mensal do IVA?"
- "Ha algum erro de validacao neste ficheiro?"
- "Lista as faturas do cliente XPTO no 3o trimestre"
- "Que percentagem da faturacao vem dos 5 maiores clientes?"

---

## Configuracao

Todas as definicoes sao configuraveis por variaveis de ambiente com o prefixo `SAFT_MCP_`:

| Variavel | Default | Descricao |
|----------|---------|-----------|
| `SAFT_MCP_STREAMING_THRESHOLD_BYTES` | 52428800 (50 MB) | Ficheiros acima deste valor usam streaming |
| `SAFT_MCP_MAX_FILE_SIZE_BYTES` | 524288000 (500 MB) | Tamanho maximo de ficheiro aceite |
| `SAFT_MCP_SESSION_TIMEOUT_SECONDS` | 1800 (30 min) | Expiracao de sessao apos inatividade |
| `SAFT_MCP_MAX_CONCURRENT_SESSIONS` | 5 | Maximo de ficheiros carregados em simultaneo |
| `SAFT_MCP_DEFAULT_QUERY_LIMIT` | 50 | Resultados por pagina por defeito |
| `SAFT_MCP_MAX_QUERY_LIMIT` | 500 | Maximo de resultados por pagina |
| `SAFT_MCP_LOG_LEVEL` | INFO | Nivel de logging |

---

## Arquitectura

```
Assistente IA (Claude, Cursor, etc.)
        |
        | Protocolo MCP (stdio)
        v
+------------------------------------------+
|           servidor saft-mcp              |
|                                          |
|  server.py       Ponto de entrada        |
|  state.py        Gestao de sessoes       |
|                                          |
|  parser/                                 |
|    detector.py   Detecao de namespace    |
|    encoding.py   Tratamento de charset   |
|    full_parser.py   Parse DOM (< 50 MB)  |
|    models.py     Modelos Pydantic        |
|                                          |
|  tools/                                  |
|    load.py       saft_load               |
|    validate.py   saft_validate           |
|    summary.py    saft_summary            |
|    query_invoices.py  saft_query_invoices|
|    tax_summary.py     saft_tax_summary   |
|                                          |
|  validators/                             |
|    xsd_validator.py   XSD 1.04_01        |
|    business_rules.py  Numeracao, totais  |
|    nif.py             NIF mod-11         |
|    hash_chain.py      Continuidade hash  |
|                                          |
|  schemas/                                |
|    saftpt1.04_01.xsd  XSD oficial        |
+------------------------------------------+
```

Decisoes de design:

- **Todos os valores monetarios usam `Decimal`** para evitar erros de arredondamento em calculos fiscais
- **lxml** para parsing XML, com stripping automatico de funcionalidades XSD 1.1 (o XSD oficial portugues usa `xs:assert` e `xs:all` com filhos unbounded, que o motor XSD 1.0 do lxml nao suporta nativamente)
- **Modelos Pydantic v2** validados contra exportacoes reais do PHC Corporate
- **Detecao automatica de namespace** lendo os primeiros 4 KB do ficheiro (nunca hardcoded)
- **Encoding Windows-1252** tratado nativamente pela declaracao XML

---

## Desenvolvimento

```bash
# Instalar com dependencias de desenvolvimento
uv sync --extra dev

# Correr testes (82 testes)
pytest

# Lint
ruff check src/ tests/

# Formatar
ruff format src/ tests/

# Verificacao de tipos
mypy src/
```

---

## Versoes SAF-T suportadas

- **SAF-T PT 1.04_01** (norma portuguesa atual)

Testado com exportacoes reais do PHC Corporate. Deve funcionar com ficheiros SAF-T de qualquer software portugues compativel (Sage, Primavera, PHC, Moloni, InvoiceXpress, etc.).

---

## Licenca

MIT

---

Desenvolvido por [bybloom.ai](https://bybloom.ai), uma unidade de negocio da [Bloomidea](https://bloomidea.com)
