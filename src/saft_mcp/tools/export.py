"""saft_export tool -- Export query results to CSV."""

from __future__ import annotations

import csv
from pathlib import Path

from saft_mcp.state import SessionState
from saft_mcp.tools.anomaly_detect import detect_anomalies
from saft_mcp.tools.query_customers import query_customers
from saft_mcp.tools.query_invoices import query_invoices
from saft_mcp.tools.query_products import query_products
from saft_mcp.tools.tax_summary import tax_summary

VALID_EXPORT_TYPES = ["invoices", "customers", "products", "tax_summary", "anomalies"]


def export_csv(
    session: SessionState,
    export_type: str,
    file_path: str,
    filters: dict | None = None,
) -> dict:
    """Export query results to a CSV file."""
    if session.loaded_file is None:
        return {
            "error": "No SAF-T file loaded. Use saft_load first.",
            "suggestion": "Call saft_load with the path to your SAF-T XML file.",
        }

    if export_type not in VALID_EXPORT_TYPES:
        return {
            "error": f"Invalid export_type '{export_type}'.",
            "suggestion": f"Valid types: {', '.join(VALID_EXPORT_TYPES)}",
        }

    f = filters or {}

    if export_type == "invoices":
        return _export_invoices(session, file_path, f)
    if export_type == "customers":
        return _export_customers(session, file_path, f)
    if export_type == "products":
        return _export_products(session, file_path, f)
    if export_type == "tax_summary":
        return _export_tax_summary(session, file_path, f)
    if export_type == "anomalies":
        return _export_anomalies(session, file_path, f)

    return {"error": "Unknown export type"}


def _write_csv(file_path: str, columns: list[str], rows: list[dict]) -> dict:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return {
        "file_path": str(path.resolve()),
        "row_count": len(rows),
        "columns": columns,
    }


def _export_invoices(session: SessionState, file_path: str, filters: dict) -> dict:
    result = query_invoices(session, limit=500, **filters)
    if "error" in result:
        return result
    columns = [
        "invoice_no", "invoice_date", "invoice_type", "customer_id",
        "customer_name", "net_total", "tax_payable", "gross_total",
        "status", "line_count",
    ]
    return _write_csv(file_path, columns, result["invoices"])


def _export_customers(session: SessionState, file_path: str, filters: dict) -> dict:
    result = query_customers(session, limit=500, **filters)
    if "error" in result:
        return result
    # Flatten billing address
    rows = []
    for c in result["customers"]:
        row = {**c}
        addr = row.pop("billing_address", {})
        row["address_detail"] = addr.get("address_detail", "")
        row["city"] = addr.get("city", "")
        row["postal_code"] = addr.get("postal_code", "")
        row["country"] = addr.get("country", "")
        rows.append(row)
    columns = [
        "customer_id", "customer_tax_id", "company_name",
        "address_detail", "city", "postal_code", "country",
        "self_billing_indicator", "invoice_count", "total_revenue",
    ]
    return _write_csv(file_path, columns, rows)


def _export_products(session: SessionState, file_path: str, filters: dict) -> dict:
    result = query_products(session, limit=500, **filters)
    if "error" in result:
        return result
    columns = [
        "product_code", "product_description", "product_type",
        "product_group", "product_number_code",
        "times_sold", "total_quantity", "total_revenue",
    ]
    return _write_csv(file_path, columns, result["products"])


def _export_tax_summary(session: SessionState, file_path: str, filters: dict) -> dict:
    result = tax_summary(session, **filters)
    if "error" in result:
        return result
    columns = [
        "group_key", "tax_percentage", "taxable_base",
        "tax_amount", "gross_total", "invoice_count",
    ]
    return _write_csv(file_path, columns, result["entries"])


def _export_anomalies(session: SessionState, file_path: str, filters: dict) -> dict:
    checks = filters.get("checks")
    result = detect_anomalies(session, checks=checks)
    if "error" in result:
        return result
    rows = []
    for a in result["anomalies"]:
        rows.append({
            "type": a["type"],
            "severity": a["severity"],
            "description": a["description"],
            "affected_documents": "; ".join(a["affected_documents"]),
        })
    columns = ["type", "severity", "description", "affected_documents"]
    return _write_csv(file_path, columns, rows)
