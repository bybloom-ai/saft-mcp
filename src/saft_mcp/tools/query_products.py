"""saft_query_products tool -- Search and filter product catalog."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from saft_mcp.config import settings
from saft_mcp.state import SessionState


def query_products(
    session: SessionState,
    description: str | None = None,
    code: str | None = None,
    product_type: str | None = None,
    group: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict:
    """Query products with filtering, pagination, and sales stats."""
    if session.loaded_file is None:
        return {
            "error": "No SAF-T file loaded. Use saft_load first.",
            "suggestion": "Call saft_load with the path to your SAF-T XML file.",
        }

    data = session.loaded_file
    effective_limit = min(limit or settings.default_query_limit, settings.max_query_limit)

    # Pre-compute sales stats per product (excluding cancelled invoices)
    prod_times_sold: defaultdict[str, int] = defaultdict(int)
    prod_total_qty: defaultdict[str, Decimal] = defaultdict(Decimal)
    prod_total_revenue: defaultdict[str, Decimal] = defaultdict(Decimal)
    for inv in data.invoices:
        if inv.document_status.invoice_status == "A":
            continue
        sign = Decimal("-1") if inv.invoice_type == "NC" else Decimal("1")
        for line in inv.lines:
            pc = line.product_code
            prod_times_sold[pc] += 1
            prod_total_qty[pc] += line.quantity * sign
            amount = line.credit_amount if line.credit_amount else line.debit_amount
            prod_total_revenue[pc] += amount * sign

    # Filter products
    filtered = []
    for prod in data.products:
        if description and description.lower() not in prod.product_description.lower():
            continue
        if code and code not in prod.product_code:
            continue
        if product_type and prod.product_type != product_type.upper():
            continue
        if group and group.lower() not in prod.product_group.lower():
            continue
        filtered.append(prod)

    total_count = len(filtered)
    page = filtered[offset : offset + effective_limit]

    products_out = [
        {
            "product_code": p.product_code,
            "product_description": p.product_description,
            "product_type": p.product_type,
            "product_group": p.product_group,
            "product_number_code": p.product_number_code,
            "times_sold": prod_times_sold.get(p.product_code, 0),
            "total_quantity": str(
                prod_total_qty.get(p.product_code, Decimal("0")).quantize(Decimal("0.01"))
            ),
            "total_revenue": str(
                prod_total_revenue.get(p.product_code, Decimal("0")).quantize(Decimal("0.01"))
            ),
        }
        for p in page
    ]

    return {
        "total_count": total_count,
        "returned_count": len(page),
        "offset": offset,
        "has_more": offset + len(page) < total_count,
        "products": products_out,
    }
