# Query Tools Design: Customers, Products, Invoice Detail

Date: 2025-02-25

## Overview

Three new tools to fill gaps in the MVP:
1. `saft_query_customers` - search/filter customer master data with revenue stats
2. `saft_query_products` - search/filter product catalog with sales stats
3. `saft_get_invoice` - full invoice detail including line items

## Tool 1: saft_query_customers

File: `src/saft_mcp/tools/query_customers.py`

Parameters:
- `name` (str) - case-insensitive partial match on company_name
- `nif` (str) - partial match on customer_tax_id
- `city` (str) - case-insensitive partial match on billing_address.city
- `country` (str) - exact match on billing_address.country
- `limit` (int) - default 50, max 500
- `offset` (int) - pagination offset

Returns per customer:
- customer_id, customer_tax_id, company_name
- billing_address (address_detail, city, postal_code, country)
- self_billing_indicator
- invoice_count (excluding cancelled and NC)
- total_revenue (excluding cancelled and NC)

## Tool 2: saft_query_products

File: `src/saft_mcp/tools/query_products.py`

Parameters:
- `description` (str) - case-insensitive partial on product_description
- `code` (str) - partial match on product_code
- `product_type` (str) - exact match: P, S, O, I, E
- `group` (str) - case-insensitive partial on product_group
- `limit` (int) - default 50, max 500
- `offset` (int) - pagination offset

Returns per product:
- product_code, product_description, product_type, product_group, product_number_code
- times_sold (invoice line count, excluding cancelled invoices)
- total_quantity
- total_revenue (sum of credit_amount/debit_amount from lines)

## Tool 3: saft_get_invoice

File: `src/saft_mcp/tools/get_invoice.py`

Parameters:
- `invoice_no` (str) - exact invoice number e.g. "FR 2025A15/90"

Returns:
- Full header: invoice_no, date, type, status, atcud, hash, customer info
- document_totals: net_total, tax_payable, gross_total, currency
- special_regimes
- lines[]: line_number, product_code, product_description, quantity,
  unit_of_measure, unit_price, credit/debit_amount, tax details,
  exemption info, settlement, references (for NC lines)

## Implementation

- Follow existing tool patterns (function in tool file, register in server.py)
- Tests mirror existing structure (test_query_customers.py, test_query_products.py, test_get_invoice.py)
- Revenue stats computed by iterating invoices once and building lookup dicts
