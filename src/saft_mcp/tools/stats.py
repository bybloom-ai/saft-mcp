"""saft_stats tool -- Statistical overview of SAF-T data."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from statistics import mean, median, stdev
from typing import Any

from saft_mcp.state import SessionState


def compute_stats(
    session: SessionState,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """Compute statistical overview of the loaded SAF-T data."""
    if session.loaded_file is None:
        return {
            "error": "No SAF-T file loaded. Use saft_load first.",
            "suggestion": "Call saft_load with the path to your SAF-T XML file.",
        }

    data = session.loaded_file
    df = date.fromisoformat(date_from) if date_from else None
    dt = date.fromisoformat(date_to) if date_to else None

    # Collect non-cancelled, non-NC invoices
    amounts: list[float] = []
    daily_counts: defaultdict[str, int] = defaultdict(int)
    weekday_counts: defaultdict[int, int] = defaultdict(int)
    monthly_counts: defaultdict[str, int] = defaultdict(int)
    monthly_revenue: defaultdict[str, Decimal] = defaultdict(Decimal)
    customer_revenue: defaultdict[str, Decimal] = defaultdict(Decimal)
    top_inv = None
    top_amount = Decimal("-1")
    bottom_inv = None
    bottom_amount: Decimal | None = None

    for inv in data.invoices:
        if inv.document_status.invoice_status == "A":
            continue
        if df and inv.invoice_date < df:
            continue
        if dt and inv.invoice_date > dt:
            continue
        if inv.invoice_type == "NC":
            continue

        gross = inv.document_totals.gross_total
        amounts.append(float(gross))

        day_key = inv.invoice_date.isoformat()
        daily_counts[day_key] += 1

        weekday_counts[inv.invoice_date.weekday()] += 1

        month_key = f"{inv.invoice_date.year}-{inv.invoice_date.month:02d}"
        monthly_counts[month_key] += 1
        monthly_revenue[month_key] += gross

        customer_revenue[inv.customer_id] += gross

        if gross > top_amount:
            top_amount = gross
            top_inv = inv
        if bottom_amount is None or gross < bottom_amount:
            bottom_amount = gross
            bottom_inv = inv

    if not amounts:
        return {
            "error": "No invoices match the given filters.",
            "suggestion": "Try a wider date range or remove filters.",
        }

    # Invoice stats
    avg = mean(amounts)
    med = median(amounts)
    sd = stdev(amounts) if len(amounts) > 1 else 0.0
    inv_min = min(amounts)
    inv_max = max(amounts)

    # Daily stats
    daily_values = list(daily_counts.values())
    avg_per_day = mean(daily_values) if daily_values else 0
    busiest_day = max(daily_counts.items(), key=lambda x: x[1])
    quietest_day = min(daily_counts.items(), key=lambda x: x[1])

    # Weekday distribution
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_dist = [
        {"weekday": weekday_names[i], "count": weekday_counts.get(i, 0)} for i in range(7)
    ]

    # Monthly distribution
    monthly_dist = [
        {
            "month": month,
            "count": monthly_counts[month],
            "revenue": str(monthly_revenue[month].quantize(Decimal("0.01"))),
        }
        for month in sorted(monthly_counts.keys())
    ]

    # Customer concentration (Pareto)
    sorted_revenue = sorted(customer_revenue.values(), reverse=True)
    total_rev = sum(sorted_revenue)
    concentration = {}
    for n in [1, 5, 10, 20]:
        top_n = sum(sorted_revenue[:n]) if len(sorted_revenue) >= n else sum(sorted_revenue)
        pct = float(top_n / total_rev * 100) if total_rev else 0
        concentration[f"top_{n}"] = {
            "customers": min(n, len(sorted_revenue)),
            "revenue": str(Decimal(str(top_n)).quantize(Decimal("0.01"))),
            "share_pct": round(pct, 1),
        }

    # Build customer name lookup for top/bottom
    cust_names = {c.customer_id: c.company_name for c in data.customers}

    result: dict[str, Any] = {
        "invoice_stats": {
            "count": len(amounts),
            "mean": round(avg, 2),
            "median": round(med, 2),
            "min": round(inv_min, 2),
            "max": round(inv_max, 2),
            "std_deviation": round(sd, 2),
        },
        "daily_stats": {
            "avg_per_day": round(avg_per_day, 1),
            "busiest_day": {"date": busiest_day[0], "count": busiest_day[1]},
            "quietest_day": {"date": quietest_day[0], "count": quietest_day[1]},
            "active_days": len(daily_counts),
        },
        "weekday_distribution": weekday_dist,
        "monthly_distribution": monthly_dist,
        "customer_concentration": concentration,
    }

    if top_inv:
        result["top_invoice"] = {
            "invoice_no": top_inv.invoice_no,
            "date": top_inv.invoice_date.isoformat(),
            "gross_total": str(top_inv.document_totals.gross_total),
            "customer_name": cust_names.get(top_inv.customer_id, top_inv.customer_id),
        }

    if bottom_inv:
        result["bottom_invoice"] = {
            "invoice_no": bottom_inv.invoice_no,
            "date": bottom_inv.invoice_date.isoformat(),
            "gross_total": str(bottom_inv.document_totals.gross_total),
            "customer_name": cust_names.get(bottom_inv.customer_id, bottom_inv.customer_id),
        }

    return result
