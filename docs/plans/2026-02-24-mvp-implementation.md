# MVP Implementation Plan

**Date:** 2026-02-24
**Scope:** v0.1 -- 5 tools: saft_load, saft_validate, saft_summary, saft_query_invoices, saft_tax_summary
**Design:** saft-mcp-technical-spec.md v1.2 (all decisions resolved)

## Build Order

The dependency graph dictates the sequence. Each step produces testable output.

### Step 1: Project scaffold + models
- `pyproject.toml` with all dependencies
- `src/saft_mcp/__init__.py`
- `src/saft_mcp/exceptions.py` -- exception hierarchy
- `src/saft_mcp/config.py` -- SaftMcpSettings
- `src/saft_mcp/parser/models.py` -- all Pydantic models from spec Section 4.1
- Test: models can be instantiated and serialized

### Step 2: Parser foundation
- `src/saft_mcp/parser/encoding.py` -- BOM stripping, encoding detection
- `src/saft_mcp/parser/detector.py` -- namespace detection, file type detection
- `src/saft_mcp/parser/full_parser.py` -- full DOM parse using lxml
- Test against real files in `Saft Josefinas 2025/`

### Step 3: State management + server shell
- `src/saft_mcp/state.py` -- SessionStore, SessionState
- `src/saft_mcp/server.py` -- FastMCP entry point (empty tool stubs)
- Test: server starts, session store works

### Step 4: saft_load tool
- `src/saft_mcp/tools/load.py`
- Wires parser + state + file validation
- Test: load real file, verify metadata returned

### Step 5: Validators
- `src/saft_mcp/validators/nif.py` -- NIF mod-11
- `src/saft_mcp/validators/hash_chain.py` -- hash chain verification
- `src/saft_mcp/validators/business_rules.py` -- numbering, ATCUD, tax codes
- `src/saft_mcp/validators/xsd_validator.py` -- XSD schema validation
- Test each validator independently against real data

### Step 6: saft_validate tool
- `src/saft_mcp/tools/validate.py`
- Orchestrates all validators, returns ValidateResponse
- Test: validate real files, check results

### Step 7: saft_summary tool
- `src/saft_mcp/tools/summary.py`
- Aggregates from loaded SaftData
- Test: summary matches manual counts from real files

### Step 8: saft_query_invoices tool
- `src/saft_mcp/tools/query_invoices.py`
- Filtering + pagination
- Test: filter by date, customer, type, amount

### Step 9: saft_tax_summary tool
- `src/saft_mcp/tools/tax_summary.py`
- VAT aggregation by rate/month/doc_type
- Test: tax totals match real file

### Step 10: Integration + polish
- Test full workflow: load -> validate -> summary -> query -> tax
- Logging decorator on all tools
- README.md with usage instructions

## Verification
Each step is verified against the real SAF-T files before moving to the next.
