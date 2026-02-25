<div align="center">

# SAF-T MCP Server

**Parse and analyze Portuguese SAF-T tax files with AI assistants**

[![PyPI](https://img.shields.io/pypi/v/saft-mcp?style=flat-square)](https://pypi.org/project/saft-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/bybloom-ai/saft-mcp/ci.yml?style=flat-square&label=CI)](https://github.com/bybloom-ai/saft-mcp/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![SAF-T PT 1.04_01](https://img.shields.io/badge/SAF--T%20PT-1.04__01-green?style=flat-square)](https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/SAFT_PT/Paginas/news-saf-t-702.aspx)

[Getting Started](#quick-start) &#183; [Available Tools](#available-tools) &#183; [Configuration](#configuration)

*[Versao em Portugues](README.pt.md)* &#183; *13 tools &#183; 152 tests*

</div>

---

A **Model Context Protocol (MCP) server** that enables AI assistants like Claude, Cursor, and Windsurf to load, validate, and analyze Portuguese [SAF-T](https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/SAFT_PT/Paginas/default.aspx) (Standard Audit File for Tax Purposes) XML files. Load a SAF-T file and immediately query invoices, get revenue summaries, VAT breakdowns, and validate compliance with Portuguese tax rules.

### What is SAF-T PT?

SAF-T PT is a mandatory XML file that all Portuguese companies must be able to export from their accounting/billing software. It contains the company's invoices, payments, customers, products, tax entries, and more. This MCP server turns that XML into a queryable data source for AI assistants.

---

## Quick Start

### Prerequisites

- **Python 3.11+** and [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A **SAF-T PT XML file** exported from any Portuguese billing/accounting software (PHC, Sage, Primavera, etc.)

### 1. Install

```bash
pip install saft-mcp
```

Or from source:

```bash
git clone https://github.com/bybloom-ai/saft-mcp.git
cd saft-mcp
uv sync
```

### 2. Add to your AI assistant

<details open>
<summary><strong>Claude Code</strong></summary>

```bash
claude mcp add saft-mcp -- /path/to/saft-mcp/.venv/bin/python -m saft_mcp
```
</details>

<details>
<summary><strong>Claude Desktop</strong></summary>

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "saft-mcp": {
      "command": "/path/to/saft-mcp/.venv/bin/python",
      "args": ["-m", "saft_mcp"]
    }
  }
}
```
</details>

<details>
<summary><strong>Cursor / VS Code / Other MCP clients</strong></summary>

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "saft-mcp": {
      "command": "/path/to/saft-mcp/.venv/bin/python",
      "args": ["-m", "saft_mcp"]
    }
  }
}
```
</details>

### 3. Start using it

Ask your AI assistant:

> "Load my SAF-T file at ~/Documents/saft_2025.xml and give me a revenue summary"

The server will parse the file, extract all invoices and tax data, and make it available for querying through natural conversation.

---

## Available Tools

### `saft_load`

Load and parse a SAF-T PT XML file. This must be called first before using any other tool.

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | string | Path to the SAF-T XML file |

Returns company name, NIF, fiscal period, SAF-T version, and record counts (customers, products, invoices, payments).

Handles Windows-1252 and UTF-8 encodings, BOM stripping, and automatic namespace detection. Files under 50 MB are parsed with full DOM; larger files use streaming.

---

### `saft_validate`

Validate the loaded file against the official XSD schema and Portuguese business rules.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rules` | list[string] | all | Specific rules to check |

Available rules:

| Rule | What it checks |
|------|---------------|
| `xsd` | XML structure against SAF-T PT 1.04_01 XSD schema |
| `numbering` | Sequential invoice numbering within each series |
| `nif` | NIF (tax ID) mod-11 check digit validation |
| `tax_codes` | Tax percentages match known Portuguese VAT rates |
| `atcud` | ATCUD unique document codes are present and well-formed |
| `hash_chain` | Hash continuity across invoice sequences |
| `control_totals` | Calculated totals match declared control totals |

Returns results with severity (error/warning), location, and fix suggestions.

---

### `saft_summary`

Generate an executive summary of the loaded file. No parameters needed.

Returns:
- Revenue totals (gross, credit notes, net)
- Invoice and credit note counts
- VAT breakdown by rate
- Top 10 customers by revenue
- Document type distribution (FT, FR, NC, ND, FS)

---

### `saft_query_invoices`

Search and filter invoices with full pagination.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date_from` | string | - | Start date (YYYY-MM-DD) |
| `date_to` | string | - | End date (YYYY-MM-DD) |
| `customer_nif` | string | - | Filter by tax ID (partial match) |
| `customer_name` | string | - | Filter by name (case-insensitive, partial) |
| `doc_type` | string | - | FT, FR, NC, ND, or FS |
| `min_amount` | number | - | Minimum gross total |
| `max_amount` | number | - | Maximum gross total |
| `status` | string | - | N (normal), A (cancelled), F (invoiced) |
| `limit` | integer | 50 | Results per page (max 500) |
| `offset` | integer | 0 | Pagination offset |

Returns matching invoices with document number, date, type, customer, amounts, status, and line count.

---

### `saft_tax_summary`

Generate a VAT analysis grouped by rate, month, or document type.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date_from` | string | - | Start date (YYYY-MM-DD) |
| `date_to` | string | - | End date (YYYY-MM-DD) |
| `group_by` | string | `rate` | Group by `rate`, `month`, or `doc_type` |

Returns taxable base, VAT amount, and gross total per group, plus overall totals.

---

### `saft_query_customers`

Search and filter customer master data with revenue enrichment.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | - | Company name (case-insensitive, partial) |
| `nif` | string | - | Tax ID (partial match) |
| `city` | string | - | Billing city (case-insensitive, partial) |
| `country` | string | - | Country code (exact, e.g. "PT", "ES") |
| `limit` | integer | 50 | Results per page (max 500) |
| `offset` | integer | 0 | Pagination offset |

Returns customers with invoice count and total revenue per customer.

---

### `saft_query_products`

Search and filter the product catalog with sales statistics.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `description` | string | - | Product description (case-insensitive, partial) |
| `code` | string | - | Product code (partial match) |
| `product_type` | string | - | P (product), S (service), O (other), I (import), E (export) |
| `group` | string | - | Product group (case-insensitive, partial) |
| `limit` | integer | 50 | Results per page (max 500) |
| `offset` | integer | 0 | Pagination offset |

Returns products with times sold, total quantity, and total revenue.

---

### `saft_get_invoice`

Get full detail for a single invoice including all line items.

| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_no` | string | Exact invoice number (e.g. "FR 2025A15/90") |

Returns complete invoice with header, document totals, special regimes, and all lines with product, quantity, price, tax, exemptions, and references.

---

### `saft_anomaly_detect`

Detect suspicious patterns and irregularities in the loaded file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `checks` | list[string] | all | Specific checks to run |

Available checks:

| Check | What it detects |
|-------|----------------|
| `duplicate_invoices` | Same customer + amount + date combinations |
| `numbering_gaps` | Missing sequential numbers within each series |
| `weekend_invoices` | Invoices issued on Saturdays or Sundays |
| `unusual_amounts` | Invoice amounts > 3 standard deviations from the mean |
| `cancelled_ratio` | High cancellation rates per series |
| `zero_amount` | Invoices with zero gross total |

Returns anomalies with type, severity, description, and affected documents.

---

### `saft_compare`

Compare the loaded SAF-T file against a second file (e.g. month-over-month, year-over-year).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | string | - | Path to the second SAF-T XML file |
| `metrics` | list[string] | all | Metrics to compare |

Available metrics: `revenue`, `customers`, `products`, `doc_types`, `vat`.

Returns period labels and a changes dict with before/after/delta per metric. Includes top new/lost customers, top movers, and percentage changes.

---

### `saft_aging`

Compute accounts receivable aging from invoices and payments.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `reference_date` | string | today | Date to age from (YYYY-MM-DD) |
| `buckets` | list[int] | [30,60,90,120] | Aging bucket boundaries in days |

Returns per-customer aging with amounts in each bucket, sorted by total outstanding. Uses FIFO allocation of payments against invoices.

---

### `saft_export`

Export data to CSV files for use in spreadsheets or other tools.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `export_type` | string | - | `invoices`, `customers`, `products`, `tax_summary`, or `anomalies` |
| `file_path` | string | - | Output CSV file path |
| `filters` | dict | - | Optional filters (same as corresponding query tool) |

Returns file path, row count, and column names.

---

### `saft_stats`

Generate a statistical overview of invoicing data.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date_from` | string | - | Start date (YYYY-MM-DD) |
| `date_to` | string | - | End date (YYYY-MM-DD) |

Returns invoice statistics (mean, median, std deviation), daily/weekly/monthly distributions, customer concentration (Pareto analysis), and top/bottom invoices.

---

## Typical Workflow

```
1. saft_load            -> Parse the XML file
2. saft_validate        -> Check compliance (XSD + business rules)
3. saft_summary         -> Get the big picture (revenue, top customers, VAT)
4. saft_query_invoices  -> Drill into specific invoices
5. saft_get_invoice     -> Full detail for a single invoice
6. saft_tax_summary     -> VAT analysis by rate, month, or doc type
7. saft_anomaly_detect  -> Flag suspicious patterns
8. saft_stats           -> Statistical distributions and trends
9. saft_compare         -> Diff against another SAF-T file
10. saft_export         -> Export results to CSV
```

Example questions you can ask after loading a file:

- "How much revenue did the company make this year?"
- "Show me all credit notes above 500 euros"
- "What's the monthly VAT breakdown?"
- "Are there any validation errors in this file?"
- "List invoices for customer XPTO in Q3"
- "What percentage of revenue comes from the top 5 customers?"
- "Are there any suspicious patterns or anomalies?"
- "Compare this file against last month's SAF-T"
- "What's the accounts receivable aging?"
- "Export all invoices to CSV"

---

## Configuration

All settings are configurable via environment variables with the `SAFT_MCP_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `SAFT_MCP_STREAMING_THRESHOLD_BYTES` | 52428800 (50 MB) | Files above this use streaming parser |
| `SAFT_MCP_MAX_FILE_SIZE_BYTES` | 524288000 (500 MB) | Maximum file size accepted |
| `SAFT_MCP_SESSION_TIMEOUT_SECONDS` | 1800 (30 min) | Session expiry after inactivity |
| `SAFT_MCP_MAX_CONCURRENT_SESSIONS` | 5 | Maximum simultaneous loaded files |
| `SAFT_MCP_DEFAULT_QUERY_LIMIT` | 50 | Default results per page |
| `SAFT_MCP_MAX_QUERY_LIMIT` | 500 | Maximum results per page |
| `SAFT_MCP_LOG_LEVEL` | INFO | Logging level |

---

## Architecture

```
AI Assistant (Claude, Cursor, etc.)
        |
        | MCP Protocol (stdio)
        v
+------------------------------------------+
|           saft-mcp server                |
|                                          |
|  server.py       FastMCP entry point     |
|  state.py        Session management      |
|                                          |
|  parser/                                 |
|    detector.py   Namespace detection     |
|    encoding.py   Charset handling        |
|    full_parser.py   DOM parse (< 50 MB)  |
|    models.py     Pydantic data models    |
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
|    business_rules.py  Numbering, totals  |
|    nif.py             NIF mod-11         |
|    hash_chain.py      Hash continuity    |
|                                          |
|  schemas/                                |
|    saftpt1.04_01.xsd  Official XSD       |
+------------------------------------------+
```

Key design decisions:

- **All monetary values use `Decimal`** to avoid floating-point rounding in tax calculations
- **lxml** for XML parsing, with automatic XSD 1.1 feature stripping (the official Portuguese XSD uses `xs:assert` and `xs:all` with unbounded children, which lxml's XSD 1.0 engine cannot handle natively)
- **Pydantic v2 models** validated against real PHC Corporate exports
- **Namespace auto-detection** by scanning the first 4 KB of the file (never hardcoded)
- **Windows-1252 encoding** handled natively via the XML declaration

---

## Development

```bash
# Install with dev dependencies
uv sync --extra dev

# Run tests (152 tests)
pytest

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type check
mypy src/
```

### Project structure

```
saft-mcp/
  src/saft_mcp/         # Source code
    server.py           # FastMCP entry point, tool registration
    config.py           # Settings (pydantic-settings, env vars)
    state.py            # Session store, parsed file state
    exceptions.py       # SaftError hierarchy
    parser/             # XML parsing (encoding, detection, models)
    tools/              # One file per MCP tool
    validators/         # XSD, business rules, NIF, hash chain
    schemas/            # Official XSD file
  tests/                # Mirrors src/ structure
  pyproject.toml        # Project config (hatch build, ruff, mypy, pytest)
```

---

## Roadmap

- [x] `saft_query_customers` -- search and filter customer master data
- [x] `saft_query_products` -- search and filter product catalog
- [x] `saft_get_invoice` -- full invoice detail with line items
- [x] `saft_anomaly_detect` -- flag duplicate invoices, numbering gaps, unusual amounts
- [x] `saft_compare` -- diff two SAF-T files (e.g. month-over-month)
- [x] `saft_aging` -- accounts receivable aging analysis
- [x] `saft_export` -- export data to CSV
- [x] `saft_stats` -- statistical overview and distributions
- [ ] **Streaming parser** for large files (>= 50 MB)
- [ ] Accounting SAF-T support (journal entries, general ledger, trial balance)
- [ ] `saft_trial_balance` -- generate trial balance from accounting data
- [ ] `saft_ies_prepare` -- pre-fill IES annual tax return fields
- [ ] `saft_cross_check` -- cross-reference invoicing vs accounting SAF-T
- [x] PyPI package (`pip install saft-mcp`)
- [x] GitHub Actions CI (pytest + ruff + mypy)

---

## Supported SAF-T versions

- **SAF-T PT 1.04_01** (current Portuguese standard)

Tested with real exports from PHC Corporate. Should work with SAF-T files from any compliant Portuguese software (Sage, Primavera, PHC, Moloni, InvoiceXpress, etc.).

---

## License

MIT

---

Built by [bybloom.ai](https://bybloom.ai), a business unit of [Bloomidea](https://bloomidea.com/en)
