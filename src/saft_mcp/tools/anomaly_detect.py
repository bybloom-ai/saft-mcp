"""saft_anomaly_detect tool -- Detect suspicious patterns in SAF-T data."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from statistics import mean, stdev

from saft_mcp.state import SessionState
from saft_mcp.validators.hash_chain import extract_number, extract_series

ALL_CHECKS = [
    "duplicate_invoices",
    "numbering_gaps",
    "weekend_invoices",
    "unusual_amounts",
    "cancelled_ratio",
    "zero_amount",
]


def detect_anomalies(
    session: SessionState,
    checks: list[str] | None = None,
) -> dict:
    """Detect anomalies in the loaded SAF-T data."""
    if session.loaded_file is None:
        return {
            "error": "No SAF-T file loaded. Use saft_load first.",
            "suggestion": "Call saft_load with the path to your SAF-T XML file.",
        }

    data = session.loaded_file
    active_checks = checks or ALL_CHECKS
    anomalies: list[dict] = []

    if "duplicate_invoices" in active_checks:
        anomalies.extend(_check_duplicates(data))

    if "numbering_gaps" in active_checks:
        anomalies.extend(_check_numbering_gaps(data))

    if "weekend_invoices" in active_checks:
        anomalies.extend(_check_weekend_invoices(data))

    if "unusual_amounts" in active_checks:
        anomalies.extend(_check_unusual_amounts(data))

    if "cancelled_ratio" in active_checks:
        anomalies.extend(_check_cancelled_ratio(data))

    if "zero_amount" in active_checks:
        anomalies.extend(_check_zero_amount(data))

    return {
        "checks_run": active_checks,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
    }


def _check_duplicates(data) -> list[dict]:
    """Same customer + same amount + same date."""
    seen: defaultdict[tuple, list[str]] = defaultdict(list)
    for inv in data.invoices:
        if inv.document_status.invoice_status == "A":
            continue
        key = (inv.customer_id, str(inv.document_totals.gross_total), inv.invoice_date.isoformat())
        seen[key].append(inv.invoice_no)

    anomalies = []
    for (cust_id, amount, inv_date), inv_nos in seen.items():
        if len(inv_nos) > 1:
            anomalies.append({
                "type": "duplicate_invoices",
                "severity": "warning",
                "description": (
                    f"{len(inv_nos)} invoices with same customer, amount ({amount}), "
                    f"and date ({inv_date})"
                ),
                "affected_documents": inv_nos,
            })
    return anomalies


def _check_numbering_gaps(data) -> list[dict]:
    """Missing sequential numbers within each series."""
    series_numbers: defaultdict[str, list[int]] = defaultdict(list)
    for inv in data.invoices:
        series = extract_series(inv.invoice_no)
        num = extract_number(inv.invoice_no)
        series_numbers[series].append(num)

    anomalies = []
    for series, numbers in series_numbers.items():
        numbers.sort()
        if len(numbers) < 2:
            continue
        gaps = []
        for i in range(1, len(numbers)):
            if numbers[i] - numbers[i - 1] > 1:
                gap_start = numbers[i - 1] + 1
                gap_end = numbers[i] - 1
                if gap_start == gap_end:
                    gaps.append(str(gap_start))
                else:
                    gaps.append(f"{gap_start}-{gap_end}")
        if gaps:
            anomalies.append({
                "type": "numbering_gaps",
                "severity": "warning",
                "description": f"Series '{series}' has gaps in numbering: {', '.join(gaps)}",
                "affected_documents": [f"{series}/{g}" for g in gaps],
            })
    return anomalies


def _check_weekend_invoices(data) -> list[dict]:
    """Invoices issued on Saturday (5) or Sunday (6)."""
    weekend_invoices = []
    for inv in data.invoices:
        if inv.document_status.invoice_status == "A":
            continue
        if inv.invoice_date.weekday() >= 5:
            day_name = "Saturday" if inv.invoice_date.weekday() == 5 else "Sunday"
            weekend_invoices.append((inv.invoice_no, inv.invoice_date.isoformat(), day_name))

    if not weekend_invoices:
        return []

    return [{
        "type": "weekend_invoices",
        "severity": "info",
        "description": f"{len(weekend_invoices)} invoices issued on weekends",
        "affected_documents": [
            f"{inv_no} ({inv_date}, {day})" for inv_no, inv_date, day in weekend_invoices
        ],
    }]


def _check_unusual_amounts(data) -> list[dict]:
    """Round numbers significantly above average."""
    amounts = []
    for inv in data.invoices:
        if inv.document_status.invoice_status == "A":
            continue
        if inv.invoice_type == "NC":
            continue
        amounts.append((inv.invoice_no, float(inv.document_totals.gross_total)))

    if len(amounts) < 10:
        return []

    values = [a[1] for a in amounts]
    avg = mean(values)
    sd = stdev(values)
    threshold = avg + 3 * sd

    anomalies = []
    for inv_no, amount in amounts:
        # Round number check: divisible by 100 and above threshold
        if amount >= threshold and amount >= 100 and amount % 100 == 0:
            anomalies.append(inv_no)

    if not anomalies:
        return []

    return [{
        "type": "unusual_amounts",
        "severity": "info",
        "description": (
            f"{len(anomalies)} invoices with round amounts above "
            f"3 standard deviations (threshold: {threshold:.2f})"
        ),
        "affected_documents": anomalies,
    }]


def _check_cancelled_ratio(data) -> list[dict]:
    """High cancellation rate per series."""
    series_total: defaultdict[str, int] = defaultdict(int)
    series_cancelled: defaultdict[str, int] = defaultdict(int)
    series_cancelled_docs: defaultdict[str, list[str]] = defaultdict(list)

    for inv in data.invoices:
        series = extract_series(inv.invoice_no)
        series_total[series] += 1
        if inv.document_status.invoice_status == "A":
            series_cancelled[series] += 1
            series_cancelled_docs[series].append(inv.invoice_no)

    anomalies = []
    for series, total in series_total.items():
        cancelled = series_cancelled.get(series, 0)
        if total >= 5 and cancelled / total > 0.1:
            pct = cancelled / total * 100
            anomalies.append({
                "type": "cancelled_ratio",
                "severity": "warning",
                "description": (
                    f"Series '{series}' has {pct:.1f}% cancellation rate "
                    f"({cancelled}/{total} invoices)"
                ),
                "affected_documents": series_cancelled_docs[series],
            })
    return anomalies


def _check_zero_amount(data) -> list[dict]:
    """Invoices with gross_total of 0."""
    zero_invoices = []
    for inv in data.invoices:
        if inv.document_status.invoice_status == "A":
            continue
        if inv.document_totals.gross_total == Decimal("0"):
            zero_invoices.append(inv.invoice_no)

    if not zero_invoices:
        return []

    return [{
        "type": "zero_amount",
        "severity": "warning",
        "description": f"{len(zero_invoices)} non-cancelled invoices with zero amount",
        "affected_documents": zero_invoices,
    }]
