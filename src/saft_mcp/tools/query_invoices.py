"""saft_query_invoices tool -- Search and filter invoices."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from saft_mcp.config import settings
from saft_mcp.parser.models import Invoice
from saft_mcp.state import SessionState


def query_invoices(
    session: SessionState,
    date_from: str | None = None,
    date_to: str | None = None,
    customer_nif: str | None = None,
    customer_name: str | None = None,
    doc_type: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """Query invoices with filtering and pagination.

    Returns an InvoiceQueryResponse-style dict.
    """
    if session.loaded_file is None:
        return {
            "error": "No SAF-T file loaded. Use saft_load first.",
            "suggestion": "Call saft_load with the path to your SAF-T XML file.",
        }

    data = session.loaded_file
    effective_limit = min(limit or settings.default_query_limit, settings.max_query_limit)

    # Build customer lookups
    cust_names = {c.customer_id: c.company_name for c in data.customers}
    cust_nifs = {c.customer_id: c.customer_tax_id for c in data.customers}

    # Parse date filters
    df = date.fromisoformat(date_from) if date_from else None
    dt = date.fromisoformat(date_to) if date_to else None

    # Filter
    filtered: list[Invoice] = []
    for inv in data.invoices:
        if df and inv.invoice_date < df:
            continue
        if dt and inv.invoice_date > dt:
            continue
        if doc_type and inv.invoice_type != doc_type.upper():
            continue
        if status and inv.document_status.invoice_status != status.upper():
            continue
        if customer_nif:
            inv_nif = cust_nifs.get(inv.customer_id, "")
            if customer_nif not in inv_nif:
                continue
        if customer_name:
            inv_name = cust_names.get(inv.customer_id, "")
            if customer_name.lower() not in inv_name.lower():
                continue
        if min_amount is not None:
            if inv.document_totals.gross_total < Decimal(str(min_amount)):
                continue
        if max_amount is not None:
            if inv.document_totals.gross_total > Decimal(str(max_amount)):
                continue
        filtered.append(inv)

    total_count = len(filtered)
    page = filtered[offset : offset + effective_limit]

    invoices_out = [
        {
            "invoice_no": inv.invoice_no,
            "invoice_date": inv.invoice_date.isoformat(),
            "invoice_type": inv.invoice_type,
            "customer_id": inv.customer_id,
            "customer_name": cust_names.get(inv.customer_id, inv.customer_id),
            "net_total": str(inv.document_totals.net_total),
            "tax_payable": str(inv.document_totals.tax_payable),
            "gross_total": str(inv.document_totals.gross_total),
            "status": inv.document_status.invoice_status,
            "line_count": len(inv.lines),
        }
        for inv in page
    ]

    return {
        "total_count": total_count,
        "returned_count": len(page),
        "offset": offset,
        "has_more": offset + len(page) < total_count,
        "invoices": invoices_out,
    }
