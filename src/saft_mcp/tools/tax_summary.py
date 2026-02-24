"""saft_tax_summary tool -- VAT analysis by rate, month, or document type."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from saft_mcp.state import SessionState


def tax_summary(
    session: SessionState,
    date_from: str | None = None,
    date_to: str | None = None,
    group_by: str = "rate",
) -> dict:
    """Generate a VAT summary grouped by rate, month, or doc_type.

    Returns a TaxSummaryResponse-style dict.
    """
    if session.loaded_file is None:
        return {
            "error": "No SAF-T file loaded. Use saft_load first.",
            "suggestion": "Call saft_load with the path to your SAF-T XML file.",
        }

    data = session.loaded_file

    df = date.fromisoformat(date_from) if date_from else None
    dt = date.fromisoformat(date_to) if date_to else None

    # group_key -> {tax_percentage, taxable_base, tax_amount, gross_total, invoice_count}
    groups: defaultdict[str, dict] = defaultdict(
        lambda: {
            "tax_percentage": Decimal("0"),
            "taxable_base": Decimal("0"),
            "tax_amount": Decimal("0"),
            "gross_total": Decimal("0"),
            "invoice_count": 0,
        }
    )

    for inv in data.invoices:
        # Skip cancelled
        if inv.document_status.invoice_status == "A":
            continue
        if df and inv.invoice_date < df:
            continue
        if dt and inv.invoice_date > dt:
            continue

        for line in inv.lines:
            # Determine sign: credit notes use debit_amount (positive reversal)
            amount = line.credit_amount if line.credit_amount else line.debit_amount
            if inv.invoice_type == "NC":
                amount = -amount  # Subtract credit notes from totals

            tax_pct = line.tax.tax_percentage
            tax_amount = amount * tax_pct / Decimal("100")

            # Determine group key
            if group_by == "rate":
                key = f"{tax_pct}%"
            elif group_by == "month":
                key = f"{inv.invoice_date.year}-{inv.invoice_date.month:02d}"
            elif group_by == "doc_type":
                key = inv.invoice_type
            else:
                key = f"{tax_pct}%"

            g = groups[key]
            g["tax_percentage"] = tax_pct
            g["taxable_base"] += amount
            g["tax_amount"] += tax_amount
            g["gross_total"] += amount + tax_amount

        # Count invoice once per group (use the first line's group key)
        if inv.lines:
            first_line = inv.lines[0]
            if group_by == "rate":
                fk = f"{first_line.tax.tax_percentage}%"
            elif group_by == "month":
                fk = f"{inv.invoice_date.year}-{inv.invoice_date.month:02d}"
            elif group_by == "doc_type":
                fk = inv.invoice_type
            else:
                fk = f"{first_line.tax.tax_percentage}%"
            groups[fk]["invoice_count"] += 1

    # Build entries
    entries = []
    for key in sorted(groups.keys()):
        g = groups[key]
        entries.append({
            "group_key": key,
            "tax_percentage": str(g["tax_percentage"]),
            "taxable_base": str(g["taxable_base"].quantize(Decimal("0.01"))),
            "tax_amount": str(g["tax_amount"].quantize(Decimal("0.01"))),
            "gross_total": str(g["gross_total"].quantize(Decimal("0.01"))),
            "invoice_count": g["invoice_count"],
        })

    # Totals
    total_base = sum(Decimal(e["taxable_base"]) for e in entries)
    total_tax = sum(Decimal(e["tax_amount"]) for e in entries)
    total_gross = sum(Decimal(e["gross_total"]) for e in entries)
    total_count = sum(e["invoice_count"] for e in entries)

    # Period
    sd = data.metadata.start_date
    ed = data.metadata.end_date
    if sd.year == ed.year and sd.month == 1 and ed.month == 12:
        period = str(data.metadata.fiscal_year)
    else:
        period = f"{sd.isoformat()} to {ed.isoformat()}"

    return {
        "period": period,
        "group_by": group_by,
        "entries": entries,
        "totals": {
            "group_key": "TOTAL",
            "tax_percentage": "",
            "taxable_base": str(total_base.quantize(Decimal("0.01"))),
            "tax_amount": str(total_tax.quantize(Decimal("0.01"))),
            "gross_total": str(total_gross.quantize(Decimal("0.01"))),
            "invoice_count": total_count,
        },
    }
