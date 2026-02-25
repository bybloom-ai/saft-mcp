"""saft_summary tool -- Generate an executive summary of the loaded SAF-T file."""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any

from saft_mcp.state import SessionState


def summarize_saft(session: SessionState) -> dict[str, Any]:
    """Generate a summary of the loaded SAF-T file.

    Returns a SummaryResponse-style dict.
    """
    if session.loaded_file is None:
        return {
            "error": "No SAF-T file loaded. Use saft_load first.",
            "suggestion": "Call saft_load with the path to your SAF-T XML file.",
        }

    data = session.loaded_file
    meta = data.metadata

    # Revenue and credit note totals (only non-cancelled)
    total_revenue = Decimal("0")
    total_credit_notes = Decimal("0")
    doc_type_dist: Counter[str] = Counter()
    customer_revenue: defaultdict[str, Decimal] = defaultdict(Decimal)
    vat_map: defaultdict[str, dict[str, Decimal]] = defaultdict(
        lambda: {"taxable_base": Decimal("0"), "tax_amount": Decimal("0")}
    )

    for inv in data.invoices:
        if inv.document_status.invoice_status == "A":
            doc_type_dist[f"{inv.invoice_type} (cancelled)"] += 1
            continue

        doc_type_dist[inv.invoice_type] += 1
        gross = inv.document_totals.gross_total

        if inv.invoice_type == "NC":
            total_credit_notes += gross
        else:
            total_revenue += gross
            customer_revenue[inv.customer_id] += gross

        # VAT breakdown from lines
        for line in inv.lines:
            pct_key = str(line.tax.tax_percentage)
            amount = line.credit_amount if line.credit_amount else line.debit_amount
            tax_amount = amount * line.tax.tax_percentage / Decimal("100")
            vat_map[pct_key]["taxable_base"] += amount
            vat_map[pct_key]["tax_amount"] += tax_amount

    # Build customer name lookup
    cust_names = {c.customer_id: c.company_name for c in data.customers}

    # Top customers by revenue
    top_customers = sorted(customer_revenue.items(), key=lambda x: x[1], reverse=True)[:10]
    top_customers_list = [
        {
            "customer_id": cid,
            "customer_name": cust_names.get(cid, cid),
            "total_revenue": str(rev),
            "invoice_count": sum(
                1
                for inv in data.invoices
                if inv.customer_id == cid
                and inv.document_status.invoice_status != "A"
                and inv.invoice_type != "NC"
            ),
        }
        for cid, rev in top_customers
    ]

    # VAT breakdown
    vat_breakdown = [
        {
            "tax_percentage": pct,
            "taxable_base": str(vals["taxable_base"].quantize(Decimal("0.01"))),
            "tax_amount": str(vals["tax_amount"].quantize(Decimal("0.01"))),
        }
        for pct, vals in sorted(vat_map.items(), key=lambda x: Decimal(x[0]), reverse=True)
    ]

    # Period string
    sd = meta.start_date
    ed = meta.end_date
    if sd.year == ed.year and sd.month == 1 and ed.month == 12:
        period = str(meta.fiscal_year)
    elif sd.month == ed.month:
        period = f"{sd.year}-{sd.month:02d}"
    else:
        period = f"{sd.isoformat()} to {ed.isoformat()}"

    return {
        "company_name": meta.company_name,
        "period": period,
        "total_revenue": str(total_revenue.quantize(Decimal("0.01"))),
        "total_credit_notes": str(total_credit_notes.quantize(Decimal("0.01"))),
        "net_revenue": str((total_revenue - total_credit_notes).quantize(Decimal("0.01"))),
        "invoice_count": sum(
            1
            for inv in data.invoices
            if inv.document_status.invoice_status != "A" and inv.invoice_type != "NC"
        ),
        "credit_note_count": sum(
            1
            for inv in data.invoices
            if inv.document_status.invoice_status != "A" and inv.invoice_type == "NC"
        ),
        "payment_count": len(data.payments),
        "customer_count": len(data.customers),
        "product_count": len(data.products),
        "vat_breakdown": vat_breakdown,
        "top_customers": top_customers_list,
        "document_type_distribution": dict(doc_type_dist),
    }
