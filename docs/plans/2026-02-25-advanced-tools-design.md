# Advanced Tools Design: Anomaly Detection, Compare, Aging, Export, Stats

Date: 2025-02-25

## Overview

5 new tools to expand SAF-T analysis capabilities:
1. `saft_anomaly_detect` - suspicious pattern detection
2. `saft_compare` - diff two SAF-T files
3. `saft_aging` - accounts receivable aging
4. `saft_export` - export results to CSV
5. `saft_stats` - statistical overview

## Tool 1: saft_anomaly_detect

File: `src/saft_mcp/tools/anomaly_detect.py`

Parameters:
- `checks` (list[str], optional) - specific checks to run, defaults to all

Checks:
- duplicate_invoices: same customer + same amount + same date
- numbering_gaps: missing sequential numbers within each series
- weekend_invoices: invoices issued on Saturday/Sunday
- unusual_amounts: round numbers significantly above average
- cancelled_ratio: high cancellation rate per series
- zero_amount: invoices with gross_total of 0

Returns: list of anomalies with type, severity (warning/info), description, affected_documents[]

## Tool 2: saft_compare

File: `src/saft_mcp/tools/compare.py`

Parameters:
- `file_path` (str) - path to second SAF-T file
- `metrics` (list[str], optional) - what to compare, defaults to all

Metrics: revenue, customers, products, doc_types, vat

Loads second file temporarily via parse_saft_file(). Does not affect primary session.

Returns: period_a, period_b, changes dict with before/after/delta per metric.

## Tool 3: saft_aging

File: `src/saft_mcp/tools/aging.py`

Parameters:
- `reference_date` (str, optional) - defaults to today
- `buckets` (list[int], optional) - defaults to [30, 60, 90, 120]

Logic: For each customer, invoices (FT/FR, non-cancelled) minus payments.
Classify by days since invoice_date vs reference_date.

Returns: per-customer aging sorted by total outstanding desc, plus totals row.

## Tool 4: saft_export

File: `src/saft_mcp/tools/export.py`

Parameters:
- `export_type` (str) - invoices, customers, products, tax_summary, anomalies
- `file_path` (str) - output CSV path
- `filters` (dict, optional) - same filters as corresponding query tool

Reuses existing query functions internally. Writes CSV with csv module.

Returns: file_path, row_count, columns

## Tool 5: saft_stats

File: `src/saft_mcp/tools/stats.py`

Parameters:
- `date_from` / `date_to` (str, optional) - filter period

Returns:
- invoice_stats: count, mean, median, min, max, std_deviation
- daily_stats: avg per day, busiest day, quietest day
- weekday_distribution: count per weekday
- monthly_distribution: count + revenue per month
- top_invoice / bottom_invoice
- customer_concentration: revenue share of top 1/5/10/20 customers
