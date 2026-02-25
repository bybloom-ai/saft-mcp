# SAF-T MCP Server

MCP server for parsing and analyzing Portuguese SAF-T (Standard Audit File for Tax Purposes) XML files. Fully implemented with 13 tools and 152 tests.

## Documents

- `saft-mcp-prd-en.md` -- Product requirements, tool specifications, business context
- `saft-mcp-technical-spec.md` (v1.2) -- **Authoritative implementation reference**. Data models, architecture decisions, all design questions resolved. Models validated against real PHC exports.

When in doubt, the tech spec wins. It was updated after analyzing real SAF-T files and supersedes the PRD on any structural detail.

## Real SAF-T Files

Located in `Saft Josefinas 2025/`. These are real exports from PHC Corporate for Bloomers S.A. (NIF 510803601).

- `5108036012025_Completo.xml` -- Full year, all sections (1.1 MB)
- `5108036012025202502031408.xml` -- Monthly export, January only (110 KB)
- 11 other monthly files (Feb-Dec)

**Encoding: Windows-1252** (declared in XML header). Not UTF-8. lxml handles this natively via the XML declaration.

## Tech Stack

- Python 3.11+, FastMCP (MCP SDK), lxml, Pydantic v2, pydantic-settings, chardet
- Dev: pytest, pytest-asyncio, ruff, mypy

## Project Structure

```
src/saft_mcp/
  server.py          # FastMCP entry point, registers all 13 tools
  config.py          # SaftMcpSettings (pydantic-settings)
  state.py           # SessionStore, SessionState
  exceptions.py      # SaftError hierarchy
  parser/
    detector.py      # Namespace detection, file type
    full_parser.py   # DOM parse (< 50 MB)
    encoding.py      # BOM stripping, charset detection
    models.py        # All Pydantic models
  tools/
    load.py          # saft_load
    validate.py      # saft_validate
    summary.py       # saft_summary
    query_invoices.py # saft_query_invoices
    query_customers.py # saft_query_customers
    query_products.py # saft_query_products
    get_invoice.py   # saft_get_invoice
    tax_summary.py   # saft_tax_summary
    anomaly_detect.py # saft_anomaly_detect
    compare.py       # saft_compare
    aging.py         # saft_aging
    export.py        # saft_export
    stats.py         # saft_stats
  validators/        # xsd_validator.py, business_rules.py, hash_chain.py, nif.py
  schemas/           # XSD files (saftpt1.04_01.xsd)
tests/               # Mirrors src/ structure (152 tests)
```

## Domain Terms

| Term | Meaning |
|------|---------|
| SAF-T PT | Portuguese XML tax audit file, mandatory for all companies |
| NIF | Tax ID number (9 digits, mod-11 check digit). Foreign tax IDs can be alphanumeric |
| ATCUD | Unique document code from AT, mandatory since 2023. Format: `JJWYYM7W-1` |
| AT | Autoridade Tributaria (Portuguese tax authority) |
| FT | Fatura (invoice) |
| FR | Fatura-Recibo (invoice-receipt, common in retail) |
| NC | Nota de Credito (credit note) |
| ND | Nota de Debito (debit note) |
| FS | Fatura Simplificada (simplified invoice) |
| GT | Guia de Transporte (transport guide) |
| RG | Recibo (receipt/payment) |
| IES | Annual corporate tax return, pre-filled from Accounting SAF-T since 2025 |
| CAE/EACCode | Economic activity code |
| Consumidor Final | Anonymous consumer, NIF 999999990 |

## Critical Implementation Rules

- **All monetary values use `Decimal`, never `float`.** Tax rounding errors are unacceptable.
- **Address field is `address_detail`, not `street`.** Matches the XSD element name `<AddressDetail>`.
- **`SpecialRegimes` is a nested model** inside Invoice, containing `self_billing_indicator`, `cash_vat_scheme_indicator`, `third_parties_billing_indicator`. It is NOT a top-level field.
- **`Currency` lives inside `DocumentTotals`**, not at Invoice level.
- **`SourceDocumentID` in payments is nested**: contains `originating_on` (invoice number) + `invoice_date`. Not a flat string.
- **Payment type `RG`** is used by PHC. The XSD also defines `RC` and `AC`. Accept all three.
- **Monthly exports have partial MasterFiles** (Customers only, no Products/TaxTable). Parser must not fail on absent sections.
- **Foreign tax IDs are alphanumeric** (e.g., Mexican RFC `JAGE741229837`). Skip NIF mod-11 for non-numeric values.
- **`"Desconhecido"` is a placeholder** used by PHC for unknown Country, City, AccountID. Treat as empty for validation.
- **Namespace detection**: read first 4 KB, regex for `urn:OECD:StandardAuditFile-Tax:PT_*`. Never hardcode.
- **Invoice numbers**: always split on last `/` to get series and sequential number. Format varies by vendor.

## Implemented Tools (13)

**Core (v0.1):** `saft_load`, `saft_validate`, `saft_summary`, `saft_query_invoices`, `saft_tax_summary`
**Query:** `saft_query_customers`, `saft_query_products`, `saft_get_invoice`
**Analysis:** `saft_anomaly_detect`, `saft_compare`, `saft_aging`, `saft_export`, `saft_stats`

## Code Style

- Ruff for linting and formatting
- Type hints everywhere, mypy strict
- Async tools (FastMCP is async)
- Each tool in its own file under `tools/`
- Tests mirror source structure
