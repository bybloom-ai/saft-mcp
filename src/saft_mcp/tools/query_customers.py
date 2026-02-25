"""saft_query_customers tool -- Search and filter customer master data."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from saft_mcp.config import settings
from saft_mcp.state import SessionState


def query_customers(
    session: SessionState,
    name: str | None = None,
    nif: str | None = None,
    city: str | None = None,
    country: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """Query customers with filtering, pagination, and revenue stats."""
    if session.loaded_file is None:
        return {
            "error": "No SAF-T file loaded. Use saft_load first.",
            "suggestion": "Call saft_load with the path to your SAF-T XML file.",
        }

    data = session.loaded_file
    effective_limit = min(limit or settings.default_query_limit, settings.max_query_limit)

    # Pre-compute revenue stats per customer (excluding cancelled and credit notes)
    cust_revenue: defaultdict[str, Decimal] = defaultdict(Decimal)
    cust_invoice_count: defaultdict[str, int] = defaultdict(int)
    for inv in data.invoices:
        if inv.document_status.invoice_status == "A":
            continue
        if inv.invoice_type == "NC":
            continue
        cust_revenue[inv.customer_id] += inv.document_totals.gross_total
        cust_invoice_count[inv.customer_id] += 1

    # Filter customers
    filtered = []
    for cust in data.customers:
        if name and name.lower() not in cust.company_name.lower():
            continue
        if nif and nif not in cust.customer_tax_id:
            continue
        if city and city.lower() not in cust.billing_address.city.lower():
            continue
        if country and cust.billing_address.country != country.upper():
            continue
        filtered.append(cust)

    total_count = len(filtered)
    page = filtered[offset : offset + effective_limit]

    customers_out = [
        {
            "customer_id": c.customer_id,
            "customer_tax_id": c.customer_tax_id,
            "company_name": c.company_name,
            "billing_address": {
                "address_detail": c.billing_address.address_detail,
                "city": c.billing_address.city,
                "postal_code": c.billing_address.postal_code,
                "country": c.billing_address.country,
            },
            "self_billing_indicator": c.self_billing_indicator,
            "invoice_count": cust_invoice_count.get(c.customer_id, 0),
            "total_revenue": str(
                cust_revenue.get(c.customer_id, Decimal("0")).quantize(Decimal("0.01"))
            ),
        }
        for c in page
    ]

    return {
        "total_count": total_count,
        "returned_count": len(page),
        "offset": offset,
        "has_more": offset + len(page) < total_count,
        "customers": customers_out,
    }
