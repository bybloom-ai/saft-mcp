<div align="center">

# SAF-T MCP Server

**Analise ficheiros SAF-T portugueses com assistentes de IA**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![SAF-T PT 1.04_01](https://img.shields.io/badge/SAF--T%20PT-1.04__01-green?style=flat-square)](https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/SAFT_PT/Paginas/news-saf-t-702.aspx)

[Instalação](#instalação) &#183; [Ferramentas](#ferramentas-disponíveis) &#183; [Configuração](#configuração)

*[English version](README.md)* &#183; *13 ferramentas &#183; 152 testes*

</div>

---

Um servidor **Model Context Protocol (MCP)** que permite a assistentes de IA como Claude, Cursor e Windsurf carregar, validar e analisar ficheiros [SAF-T](https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/SAFT_PT/Paginas/default.aspx) (Standard Audit File for Tax Purposes) portugueses. Carregue um ficheiro SAF-T e consulte faturas, obtenha resumos de faturação, análises de IVA e valide a conformidade com as regras fiscais portuguesas.

### O que é o SAF-T PT?

O SAF-T PT é um ficheiro XML obrigatório que todas as empresas portuguesas devem conseguir exportar do seu software de contabilidade/faturação. Contém as faturas, pagamentos, clientes, produtos, registos de impostos e mais. Este servidor MCP transforma esse XML numa fonte de dados consultável por assistentes de IA.

---

## Instalação

### Pré-requisitos

- **Python 3.11+** e [uv](https://docs.astral.sh/uv/) (recomendado) ou pip
- Um **ficheiro SAF-T PT XML** exportado de qualquer software de faturação/contabilidade português (PHC, Sage, Primavera, etc.)

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

Adicionar à configuração do cliente MCP:

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

### 3. Começar a usar

Pergunte ao assistente de IA:

> "Carrega o meu ficheiro SAF-T em ~/Documents/saft_2025.xml e dá-me um resumo da faturação"

O servidor analisa o ficheiro, extrai todas as faturas e dados fiscais, e disponibiliza-os para consulta em linguagem natural.

---

## Ferramentas Disponíveis

### `saft_load`

Carrega e analisa um ficheiro SAF-T PT XML. Deve ser chamado primeiro, antes de qualquer outra ferramenta.

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `file_path` | string | Caminho para o ficheiro SAF-T XML |

Devolve nome da empresa, NIF, período fiscal, versão SAF-T e contagens de registos (clientes, produtos, faturas, pagamentos).

Suporta encodings Windows-1252 e UTF-8, stripping de BOM e deteção automática de namespace. Ficheiros até 50 MB são analisados com DOM completo; ficheiros maiores usam streaming.

---

### `saft_validate`

Valida o ficheiro carregado contra o schema XSD oficial e regras de negócio portuguesas.

| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `rules` | list[string] | todas | Regras específicas a verificar |

Regras disponíveis:

| Regra | O que valida |
|-------|-------------|
| `xsd` | Estrutura XML contra o schema XSD SAF-T PT 1.04_01 |
| `numbering` | Numeração sequencial de faturas dentro de cada série |
| `nif` | Dígito de controlo mod-11 do NIF |
| `tax_codes` | Taxas de imposto correspondem às taxas de IVA portuguesas |
| `atcud` | Códigos ATCUD presentes e bem formados |
| `hash_chain` | Continuidade de hash entre sequências de faturas |
| `control_totals` | Totais calculados correspondem aos totais de controlo declarados |

Devolve resultados com severidade (erro/aviso), localização e sugestões de correção.

---

### `saft_summary`

Gera um resumo executivo do ficheiro carregado. Sem parâmetros.

Devolve:
- Totais de faturação (bruto, notas de crédito, líquido)
- Contagem de faturas e notas de crédito
- Distribuição de IVA por taxa
- Top 10 clientes por faturação
- Distribuição por tipo de documento (FT, FR, NC, ND, FS)

---

### `saft_query_invoices`

Pesquisa e filtra faturas com paginação.

| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `date_from` | string | - | Data início (YYYY-MM-DD) |
| `date_to` | string | - | Data fim (YYYY-MM-DD) |
| `customer_nif` | string | - | Filtrar por NIF (correspondência parcial) |
| `customer_name` | string | - | Filtrar por nome (case-insensitive, parcial) |
| `doc_type` | string | - | FT, FR, NC, ND ou FS |
| `min_amount` | number | - | Total bruto mínimo |
| `max_amount` | number | - | Total bruto máximo |
| `status` | string | - | N (normal), A (anulada), F (faturada) |
| `limit` | integer | 50 | Resultados por página (max 500) |
| `offset` | integer | 0 | Offset de paginação |

Devolve faturas com número de documento, data, tipo, cliente, valores, estado e número de linhas.

---

### `saft_tax_summary`

Gera uma análise de IVA agrupada por taxa, mês ou tipo de documento.

| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `date_from` | string | - | Data início (YYYY-MM-DD) |
| `date_to` | string | - | Data fim (YYYY-MM-DD) |
| `group_by` | string | `rate` | Agrupar por `rate` (taxa), `month` (mês) ou `doc_type` (tipo doc.) |

Devolve base tributável, valor de IVA e total bruto por grupo, mais totais globais.

---

### `saft_query_customers`

Pesquisar e filtrar dados mestres de clientes com enriquecimento de faturação.

| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `name` | string | - | Nome da empresa (case-insensitive, parcial) |
| `nif` | string | - | NIF (correspondência parcial) |
| `city` | string | - | Cidade de faturação (case-insensitive, parcial) |
| `country` | string | - | Código de país (exato, ex: "PT", "ES") |
| `limit` | integer | 50 | Resultados por página (max 500) |
| `offset` | integer | 0 | Offset de paginação |

Devolve clientes com contagem de faturas e faturação total por cliente.

---

### `saft_query_products`

Pesquisar e filtrar o catálogo de produtos com estatísticas de vendas.

| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `description` | string | - | Descrição do produto (case-insensitive, parcial) |
| `code` | string | - | Código do produto (correspondência parcial) |
| `product_type` | string | - | P (produto), S (serviço), O (outro), I (importação), E (exportação) |
| `group` | string | - | Grupo de produto (case-insensitive, parcial) |
| `limit` | integer | 50 | Resultados por página (max 500) |
| `offset` | integer | 0 | Offset de paginação |

Devolve produtos com vezes vendido, quantidade total e faturação total.

---

### `saft_get_invoice`

Obter detalhe completo de uma fatura incluindo todas as linhas.

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `invoice_no` | string | Número exato da fatura (ex: "FR 2025A15/90") |

Devolve fatura completa com cabeçalho, totais do documento, regimes especiais e todas as linhas com produto, quantidade, preço, imposto, isenções e referências.

---

### `saft_anomaly_detect`

Detetar padrões suspeitos e irregularidades no ficheiro carregado.

| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `checks` | list[string] | todas | Verificações específicas a executar |

Verificações disponíveis:

| Verificação | O que deteta |
|-------------|-------------|
| `duplicate_invoices` | Combinações iguais de cliente + valor + data |
| `numbering_gaps` | Números sequenciais em falta dentro de cada série |
| `weekend_invoices` | Faturas emitidas ao sábado ou domingo |
| `unusual_amounts` | Valores > 3 desvios-padrão da média |
| `cancelled_ratio` | Taxas elevadas de anulação por série |
| `zero_amount` | Faturas com total bruto zero |

Devolve anomalias com tipo, severidade, descrição e documentos afetados.

---

### `saft_compare`

Comparar o ficheiro SAF-T carregado com um segundo ficheiro (ex: mês a mês, ano a ano).

| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `file_path` | string | - | Caminho para o segundo ficheiro SAF-T XML |
| `metrics` | list[string] | todas | Métricas a comparar |

Métricas disponíveis: `revenue`, `customers`, `products`, `doc_types`, `vat`.

Devolve etiquetas de período e um dicionário de alterações com antes/depois/delta por métrica. Inclui top novos/perdidos clientes, maiores variações e percentagens.

---

### `saft_aging`

Calcular antiguidade de saldos (contas a receber) a partir de faturas e pagamentos.

| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `reference_date` | string | hoje | Data de referência (YYYY-MM-DD) |
| `buckets` | list[int] | [30,60,90,120] | Limites dos escalões em dias |

Devolve antiguidade por cliente com valores em cada escalão, ordenado por total em dívida. Usa alocação FIFO de pagamentos contra faturas.

---

### `saft_export`

Exportar dados para ficheiros CSV para uso em folhas de cálculo ou outras ferramentas.

| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `export_type` | string | - | `invoices`, `customers`, `products`, `tax_summary` ou `anomalies` |
| `file_path` | string | - | Caminho do ficheiro CSV de saída |
| `filters` | dict | - | Filtros opcionais (mesmos da ferramenta de consulta correspondente) |

Devolve caminho do ficheiro, contagem de linhas e nomes das colunas.

---

### `saft_stats`

Gerar uma visão estatística dos dados de faturação.

| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `date_from` | string | - | Data início (YYYY-MM-DD) |
| `date_to` | string | - | Data fim (YYYY-MM-DD) |

Devolve estatísticas de faturas (média, mediana, desvio-padrão), distribuições diárias/semanais/mensais, concentração de clientes (análise de Pareto) e faturas com maior e menor valor.

---

## Fluxo Típico

```
1. saft_load            -> Carregar e analisar o ficheiro XML
2. saft_validate        -> Verificar conformidade (XSD + regras de negócio)
3. saft_summary         -> Visão geral (faturação, top clientes, IVA)
4. saft_query_invoices  -> Consultar faturas específicas
5. saft_get_invoice     -> Detalhe completo de uma fatura
6. saft_tax_summary     -> Análise de IVA por taxa, mês ou tipo
7. saft_anomaly_detect  -> Detetar padrões suspeitos
8. saft_stats           -> Distribuições e tendências estatísticas
9. saft_compare         -> Comparar com outro ficheiro SAF-T
10. saft_export         -> Exportar resultados para CSV
```

Exemplos de perguntas após carregar um ficheiro:

- "Qual foi a faturação total da empresa este ano?"
- "Mostra-me todas as notas de crédito acima de 500 euros"
- "Qual é a distribuição mensal do IVA?"
- "Há algum erro de validação neste ficheiro?"
- "Lista as faturas do cliente XPTO no 3.º trimestre"
- "Que percentagem da faturação vem dos 5 maiores clientes?"
- "Há padrões suspeitos ou anomalias?"
- "Compara este ficheiro com o SAF-T do mês passado"
- "Qual é a antiguidade de saldos?"
- "Exporta todas as faturas para CSV"

---

## Configuração

Todas as definições são configuráveis por variáveis de ambiente com o prefixo `SAFT_MCP_`:

| Variável | Default | Descrição |
|----------|---------|-----------|
| `SAFT_MCP_STREAMING_THRESHOLD_BYTES` | 52428800 (50 MB) | Ficheiros acima deste valor usam streaming |
| `SAFT_MCP_MAX_FILE_SIZE_BYTES` | 524288000 (500 MB) | Tamanho máximo de ficheiro aceite |
| `SAFT_MCP_SESSION_TIMEOUT_SECONDS` | 1800 (30 min) | Expiração de sessão após inatividade |
| `SAFT_MCP_MAX_CONCURRENT_SESSIONS` | 5 | Máximo de ficheiros carregados em simultâneo |
| `SAFT_MCP_DEFAULT_QUERY_LIMIT` | 50 | Resultados por página por defeito |
| `SAFT_MCP_MAX_QUERY_LIMIT` | 500 | Máximo de resultados por página |
| `SAFT_MCP_LOG_LEVEL` | INFO | Nível de logging |

---

## Arquitetura

```
Assistente IA (Claude, Cursor, etc.)
        |
        | Protocolo MCP (stdio)
        v
+------------------------------------------+
|           servidor saft-mcp              |
|                                          |
|  server.py       Ponto de entrada        |
|  state.py        Gestão de sessões       |
|                                          |
|  parser/                                 |
|    detector.py   Deteção de namespace    |
|    encoding.py   Tratamento de charset   |
|    full_parser.py   Parse DOM (< 50 MB)  |
|    models.py     Modelos Pydantic        |
|                                          |
|  tools/                                  |
|    load.py            saft_load          |
|    validate.py        saft_validate      |
|    summary.py         saft_summary       |
|    query_invoices.py  saft_query_invoices|
|    query_customers.py saft_query_customer|
|    query_products.py  saft_query_products|
|    get_invoice.py     saft_get_invoice   |
|    tax_summary.py     saft_tax_summary   |
|    anomaly_detect.py  saft_anomaly_detect|
|    compare.py         saft_compare       |
|    aging.py           saft_aging         |
|    export.py          saft_export        |
|    stats.py           saft_stats         |
|                                          |
|  validators/                             |
|    xsd_validator.py   XSD 1.04_01        |
|    business_rules.py  Numeração, totais  |
|    nif.py             NIF mod-11         |
|    hash_chain.py      Continuidade hash  |
|                                          |
|  schemas/                                |
|    saftpt1.04_01.xsd  XSD oficial        |
+------------------------------------------+
```

Decisões de design:

- **Todos os valores monetários usam `Decimal`** para evitar erros de arredondamento em cálculos fiscais
- **lxml** para parsing XML, com stripping automático de funcionalidades XSD 1.1 (o XSD oficial português usa `xs:assert` e `xs:all` com filhos unbounded, que o motor XSD 1.0 do lxml não suporta nativamente)
- **Modelos Pydantic v2** validados contra exportações reais do PHC Corporate
- **Deteção automática de namespace** lendo os primeiros 4 KB do ficheiro (nunca hardcoded)
- **Encoding Windows-1252** tratado nativamente pela declaração XML

---

## Desenvolvimento

```bash
# Instalar com dependências de desenvolvimento
uv sync --extra dev

# Correr testes (152 testes)
pytest

# Lint
ruff check src/ tests/

# Formatar
ruff format src/ tests/

# Verificação de tipos
mypy src/
```

---

## Roadmap

- [x] `saft_query_customers` -- pesquisar e filtrar dados de clientes
- [x] `saft_query_products` -- pesquisar e filtrar catálogo de produtos
- [x] `saft_get_invoice` -- detalhe completo de fatura com linhas
- [x] `saft_anomaly_detect` -- detetar faturas duplicadas, falhas na numeração, valores atípicos
- [x] `saft_compare` -- comparar dois ficheiros SAF-T (ex: mês a mês)
- [x] `saft_aging` -- análise de antiguidade de saldos (contas a receber)
- [x] `saft_export` -- exportar dados para CSV
- [x] `saft_stats` -- visão estatística e distribuições
- [ ] **Streaming parser** para ficheiros grandes (>= 50 MB)
- [ ] Suporte para SAF-T de Contabilidade (lançamentos, razão geral, balancete)
- [ ] `saft_trial_balance` -- gerar balancete a partir dos dados contabilísticos
- [ ] `saft_ies_prepare` -- pré-preencher campos da IES (declaração anual)
- [ ] `saft_cross_check` -- cruzamento entre SAF-T de faturação e contabilidade
- [ ] Pacote PyPI (`pip install saft-mcp`)
- [ ] GitHub Actions CI (pytest + ruff + mypy)

---

## Versões SAF-T suportadas

- **SAF-T PT 1.04_01** (norma portuguesa atual)

Testado com exportações reais do PHC Corporate. Deve funcionar com ficheiros SAF-T de qualquer software português compatível (Sage, Primavera, PHC, Moloni, InvoiceXpress, etc.).

---

## Licença

MIT

---

Desenvolvido por [bybloom.ai](https://bybloom.ai), uma unidade de negócio da [Bloomidea](https://bloomidea.com)
