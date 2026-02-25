"""saft_compare tool -- Compare two SAF-T files."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.parser.models import SaftData
from saft_mcp.state import SessionState

ALL_METRICS = ["revenue", "customers", "products", "doc_types", "vat"]


def compare_saft(
    session: SessionState,
    file_path: str,
    metrics: list[str] | None = None,
) -> dict:
    """Compare the loaded SAF-T file against a second file."""
    if session.loaded_file is None:
        return {
            "error": "No SAF-T file loaded. Use saft_load first.",
            "suggestion": "Call saft_load with the path to your SAF-T XML file.",
        }

    try:
        data_b = parse_saft_file(file_path)
    except Exception as e:
        return {
            "error": f"Failed to parse comparison file: {e}",
            "suggestion": "Check the file path and format.",
        }

    data_a = session.loaded_file
    active_metrics = metrics or ALL_METRICS
    changes: dict = {}

    period_a = _period_str(data_a)
    period_b = _period_str(data_b)

    if "revenue" in active_metrics:
        changes["revenue"] = _compare_revenue(data_a, data_b)

    if "customers" in active_metrics:
        changes["customers"] = _compare_customers(data_a, data_b)

    if "products" in active_metrics:
        changes["products"] = _compare_products(data_a, data_b)

    if "doc_types" in active_metrics:
        changes["doc_types"] = _compare_doc_types(data_a, data_b)

    if "vat" in active_metrics:
        changes["vat"] = _compare_vat(data_a, data_b)

    return {
        "period_a": period_a,
        "period_b": period_b,
        "metrics_compared": active_metrics,
        "changes": changes,
    }


def _period_str(data: SaftData) -> str:
    meta = data.metadata
    sd, ed = meta.start_date, meta.end_date
    if sd.year == ed.year and sd.month == 1 and ed.month == 12:
        return str(meta.fiscal_year)
    if sd.month == ed.month:
        return f"{sd.year}-{sd.month:02d}"
    return f"{sd.isoformat()} to {ed.isoformat()}"


def _revenue_totals(data: SaftData) -> dict:
    revenue = Decimal("0")
    credit_notes = Decimal("0")
    for inv in data.invoices:
        if inv.document_status.invoice_status == "A":
            continue
        if inv.invoice_type == "NC":
            credit_notes += inv.document_totals.gross_total
        else:
            revenue += inv.document_totals.gross_total
    net = revenue - credit_notes
    return {
        "gross_revenue": revenue,
        "credit_notes": credit_notes,
        "net_revenue": net,
    }


def _compare_revenue(a: SaftData, b: SaftData) -> dict:
    ra, rb = _revenue_totals(a), _revenue_totals(b)
    result = {}
    for key in ["gross_revenue", "credit_notes", "net_revenue"]:
        va, vb = ra[key], rb[key]
        delta = vb - va
        pct = (delta / va * 100) if va else Decimal("0")
        result[key] = {
            "file_a": str(va.quantize(Decimal("0.01"))),
            "file_b": str(vb.quantize(Decimal("0.01"))),
            "delta": str(delta.quantize(Decimal("0.01"))),
            "delta_pct": str(pct.quantize(Decimal("0.1"))),
        }
    return result


def _customer_revenue(data: SaftData) -> dict[str, Decimal]:
    rev: defaultdict[str, Decimal] = defaultdict(Decimal)
    for inv in data.invoices:
        if inv.document_status.invoice_status == "A" or inv.invoice_type == "NC":
            continue
        rev[inv.customer_id] += inv.document_totals.gross_total
    return dict(rev)


def _compare_customers(a: SaftData, b: SaftData) -> dict:
    rev_a = _customer_revenue(a)
    rev_b = _customer_revenue(b)
    ids_a, ids_b = set(rev_a.keys()), set(rev_b.keys())

    # Name lookups
    names_a = {c.customer_id: c.company_name for c in a.customers}
    names_b = {c.customer_id: c.company_name for c in b.customers}
    names = {**names_a, **names_b}

    new_ids = ids_b - ids_a
    lost_ids = ids_a - ids_b
    common_ids = ids_a & ids_b

    # Top movers among common customers
    movers = []
    for cid in common_ids:
        delta = rev_b[cid] - rev_a[cid]
        if delta != Decimal("0"):
            movers.append((cid, delta))
    movers.sort(key=lambda x: abs(x[1]), reverse=True)

    return {
        "count_a": len(ids_a),
        "count_b": len(ids_b),
        "new_customers": len(new_ids),
        "lost_customers": len(lost_ids),
        "top_new": [
            {
                "customer_id": cid,
                "name": names.get(cid, cid),
                "revenue": str(rev_b[cid].quantize(Decimal("0.01"))),
            }
            for cid in sorted(
                new_ids, key=lambda x: rev_b.get(x, Decimal("0")), reverse=True
            )[:5]
        ],
        "top_lost": [
            {
                "customer_id": cid,
                "name": names.get(cid, cid),
                "revenue": str(rev_a[cid].quantize(Decimal("0.01"))),
            }
            for cid in sorted(
                lost_ids, key=lambda x: rev_a.get(x, Decimal("0")), reverse=True
            )[:5]
        ],
        "top_movers": [
            {
                "customer_id": cid,
                "name": names.get(cid, cid),
                "delta": str(delta.quantize(Decimal("0.01"))),
            }
            for cid, delta in movers[:10]
        ],
    }


def _product_stats(data: SaftData) -> dict[str, Decimal]:
    rev: defaultdict[str, Decimal] = defaultdict(Decimal)
    for inv in data.invoices:
        if inv.document_status.invoice_status == "A":
            continue
        sign = Decimal("-1") if inv.invoice_type == "NC" else Decimal("1")
        for line in inv.lines:
            amount = line.credit_amount if line.credit_amount else line.debit_amount
            rev[line.product_code] += amount * sign
    return dict(rev)


def _compare_products(a: SaftData, b: SaftData) -> dict:
    rev_a = _product_stats(a)
    rev_b = _product_stats(b)
    codes_a, codes_b = set(rev_a.keys()), set(rev_b.keys())

    return {
        "count_a": len(codes_a),
        "count_b": len(codes_b),
        "new_products": len(codes_b - codes_a),
        "removed_products": len(codes_a - codes_b),
    }


def _doc_type_counts(data: SaftData) -> dict[str, int]:
    counts: defaultdict[str, int] = defaultdict(int)
    for inv in data.invoices:
        if inv.document_status.invoice_status == "A":
            continue
        counts[inv.invoice_type] += 1
    return dict(counts)


def _compare_doc_types(a: SaftData, b: SaftData) -> dict:
    da, db = _doc_type_counts(a), _doc_type_counts(b)
    all_types = sorted(set(da.keys()) | set(db.keys()))
    return {
        dt: {
            "file_a": da.get(dt, 0),
            "file_b": db.get(dt, 0),
            "delta": db.get(dt, 0) - da.get(dt, 0),
        }
        for dt in all_types
    }


def _vat_by_rate(data: SaftData) -> dict[str, Decimal]:
    totals: defaultdict[str, Decimal] = defaultdict(Decimal)
    for inv in data.invoices:
        if inv.document_status.invoice_status == "A":
            continue
        for line in inv.lines:
            pct = str(line.tax.tax_percentage)
            amount = line.credit_amount if line.credit_amount else line.debit_amount
            tax = amount * line.tax.tax_percentage / Decimal("100")
            totals[pct] += tax
    return dict(totals)


def _compare_vat(a: SaftData, b: SaftData) -> dict:
    va, vb = _vat_by_rate(a), _vat_by_rate(b)
    all_rates = sorted(set(va.keys()) | set(vb.keys()), key=Decimal)
    return {
        rate: {
            "file_a": str(va.get(rate, Decimal("0")).quantize(Decimal("0.01"))),
            "file_b": str(vb.get(rate, Decimal("0")).quantize(Decimal("0.01"))),
            "delta": str(
                (vb.get(rate, Decimal("0")) - va.get(rate, Decimal("0"))).quantize(Decimal("0.01"))
            ),
        }
        for rate in all_rates
    }
