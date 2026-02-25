"""saft_get_invoice tool -- Get full invoice detail including line items."""

from __future__ import annotations

from typing import Any

from saft_mcp.state import SessionState


def get_invoice(session: SessionState, invoice_no: str) -> dict[str, Any]:
    """Get full detail for a single invoice by number."""
    if session.loaded_file is None:
        return {
            "error": "No SAF-T file loaded. Use saft_load first.",
            "suggestion": "Call saft_load with the path to your SAF-T XML file.",
        }

    data = session.loaded_file

    # Find the invoice
    inv = None
    for candidate in data.invoices:
        if candidate.invoice_no == invoice_no:
            inv = candidate
            break

    if inv is None:
        return {
            "error": f"Invoice '{invoice_no}' not found.",
            "suggestion": "Use saft_query_invoices to search for the correct invoice number.",
        }

    # Resolve customer info
    cust_name = ""
    cust_nif = ""
    for c in data.customers:
        if c.customer_id == inv.customer_id:
            cust_name = c.company_name
            cust_nif = c.customer_tax_id
            break

    # Build line detail
    lines_out = []
    for line in inv.lines:
        line_dict: dict[str, Any] = {
            "line_number": line.line_number,
            "product_code": line.product_code,
            "product_description": line.product_description,
            "quantity": str(line.quantity),
            "unit_of_measure": line.unit_of_measure,
            "unit_price": str(line.unit_price),
            "credit_amount": str(line.credit_amount),
            "debit_amount": str(line.debit_amount),
            "tax": {
                "tax_type": line.tax.tax_type,
                "tax_country_region": line.tax.tax_country_region,
                "tax_code": line.tax.tax_code,
                "tax_percentage": str(line.tax.tax_percentage),
            },
        }
        if line.tax_exemption_reason:
            line_dict["tax_exemption_reason"] = line.tax_exemption_reason
        if line.tax_exemption_code:
            line_dict["tax_exemption_code"] = line.tax_exemption_code
        if line.settlement_amount:
            line_dict["settlement_amount"] = str(line.settlement_amount)
        if line.references:
            line_dict["references"] = {
                "reference": line.references.reference,
                "reason": line.references.reason,
            }
        lines_out.append(line_dict)

    # Build document totals
    totals: dict[str, Any] = {
        "net_total": str(inv.document_totals.net_total),
        "tax_payable": str(inv.document_totals.tax_payable),
        "gross_total": str(inv.document_totals.gross_total),
    }
    if inv.document_totals.currency:
        totals["currency"] = {
            "currency_code": inv.document_totals.currency.currency_code,
            "currency_amount": str(inv.document_totals.currency.currency_amount),
            "exchange_rate": str(inv.document_totals.currency.exchange_rate),
        }

    result: dict[str, Any] = {
        "invoice_no": inv.invoice_no,
        "invoice_date": inv.invoice_date.isoformat(),
        "invoice_type": inv.invoice_type,
        "atcud": inv.atcud,
        "hash": inv.hash,
        "status": inv.document_status.invoice_status,
        "status_date": inv.document_status.invoice_status_date.isoformat(),
        "source_billing": inv.document_status.source_billing,
        "system_entry_date": inv.system_entry_date.isoformat(),
        "customer_id": inv.customer_id,
        "customer_name": cust_name,
        "customer_nif": cust_nif,
        "special_regimes": {
            "self_billing_indicator": inv.special_regimes.self_billing_indicator,
            "cash_vat_scheme_indicator": inv.special_regimes.cash_vat_scheme_indicator,
            "third_parties_billing_indicator": inv.special_regimes.third_parties_billing_indicator,
        },
        "document_totals": totals,
        "line_count": len(inv.lines),
        "lines": lines_out,
    }

    return result
