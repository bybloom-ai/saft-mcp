"""saft_aging tool -- Accounts receivable aging analysis."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from saft_mcp.state import SessionState

DEFAULT_BUCKETS = [30, 60, 90, 120]


def aging_analysis(
    session: SessionState,
    reference_date: str | None = None,
    buckets: list[int] | None = None,
) -> dict:
    """Compute accounts receivable aging from invoices and payments."""
    if session.loaded_file is None:
        return {
            "error": "No SAF-T file loaded. Use saft_load first.",
            "suggestion": "Call saft_load with the path to your SAF-T XML file.",
        }

    data = session.loaded_file
    ref_date = date.fromisoformat(reference_date) if reference_date else date.today()
    bucket_boundaries = sorted(buckets or DEFAULT_BUCKETS)

    # Build customer name lookup
    cust_names = {c.customer_id: c.company_name for c in data.customers}

    # Sum invoices per customer (FT and FR only, non-cancelled)
    customer_invoices: defaultdict[str, list[tuple[date, Decimal]]] = defaultdict(list)
    for inv in data.invoices:
        if inv.document_status.invoice_status == "A":
            continue
        if inv.invoice_type in ("FT", "FR"):
            customer_invoices[inv.customer_id].append(
                (inv.invoice_date, inv.document_totals.gross_total)
            )
        elif inv.invoice_type == "NC":
            # Credit notes reduce outstanding
            customer_invoices[inv.customer_id].append(
                (inv.invoice_date, -inv.document_totals.gross_total)
            )

    # Sum payments per customer (non-cancelled)
    customer_payments: defaultdict[str, Decimal] = defaultdict(Decimal)
    for pmt in data.payments:
        if pmt.document_status.payment_status == "A":
            continue
        customer_payments[pmt.customer_id] += pmt.document_totals.gross_total

    # Build bucket labels
    bucket_labels = []
    for i, boundary in enumerate(bucket_boundaries):
        if i == 0:
            bucket_labels.append(f"0-{boundary}")
        else:
            bucket_labels.append(f"{bucket_boundaries[i-1]+1}-{boundary}")
    bucket_labels.append(f">{bucket_boundaries[-1]}")

    # Compute aging per customer
    customer_aging: list[dict] = []
    totals_by_bucket: defaultdict[str, Decimal] = defaultdict(Decimal)
    grand_total = Decimal("0")

    for cust_id, invoice_list in customer_invoices.items():
        # Total invoiced
        total_invoiced = sum(amount for _, amount in invoice_list)
        # Subtract payments
        total_paid = customer_payments.get(cust_id, Decimal("0"))
        outstanding = total_invoiced - total_paid

        if outstanding <= Decimal("0"):
            continue

        # Distribute outstanding across buckets based on invoice ages
        # Oldest invoices are assumed unpaid first (FIFO)
        sorted_invoices = sorted(invoice_list, key=lambda x: x[0])
        remaining = outstanding
        cust_buckets: defaultdict[str, Decimal] = defaultdict(Decimal)

        for inv_date, amount in sorted_invoices:
            if remaining <= Decimal("0"):
                break
            if amount <= Decimal("0"):
                continue
            allocated = min(amount, remaining)
            days = (ref_date - inv_date).days
            bucket_label = _get_bucket(days, bucket_boundaries, bucket_labels)
            cust_buckets[bucket_label] += allocated
            remaining -= allocated

        cust_row = {
            "customer_id": cust_id,
            "customer_name": cust_names.get(cust_id, cust_id),
            "total_outstanding": str(outstanding.quantize(Decimal("0.01"))),
        }
        for label in bucket_labels:
            amount = cust_buckets.get(label, Decimal("0"))
            cust_row[label] = str(amount.quantize(Decimal("0.01")))
            totals_by_bucket[label] += amount

        grand_total += outstanding
        customer_aging.append(cust_row)

    # Sort by total outstanding descending
    customer_aging.sort(key=lambda x: Decimal(x["total_outstanding"]), reverse=True)

    # Totals row
    totals_row = {
        "customer_id": "TOTAL",
        "customer_name": "",
        "total_outstanding": str(grand_total.quantize(Decimal("0.01"))),
    }
    for label in bucket_labels:
        totals_row[label] = str(totals_by_bucket.get(label, Decimal("0")).quantize(Decimal("0.01")))

    return {
        "reference_date": ref_date.isoformat(),
        "buckets": bucket_labels,
        "customer_count": len(customer_aging),
        "customers": customer_aging,
        "totals": totals_row,
    }


def _get_bucket(days: int, boundaries: list[int], labels: list[str]) -> str:
    for i, boundary in enumerate(boundaries):
        if days <= boundary:
            return labels[i]
    return labels[-1]
