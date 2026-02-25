"""Tests for the saft_get_invoice tool."""

from decimal import Decimal
from pathlib import Path

import pytest

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.state import SessionState
from saft_mcp.tools.get_invoice import get_invoice
from saft_mcp.tools.query_invoices import query_invoices

REAL_DATA_DIR = Path(__file__).parent.parent.parent / "Saft Josefinas 2025"
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"


@pytest.fixture(scope="module")
def loaded_session():
    if not REAL_FULL_YEAR.exists():
        pytest.skip("Real SAF-T files not available")
    session = SessionState()
    session.loaded_file = parse_saft_file(str(REAL_FULL_YEAR))
    return session


class TestGetInvoice:
    def test_no_file_loaded(self):
        session = SessionState()
        result = get_invoice(session, invoice_no="FR 2025A15/1")
        assert "error" in result

    def test_invoice_not_found(self, loaded_session):
        result = get_invoice(loaded_session, invoice_no="NONEXISTENT/999")
        assert "error" in result
        assert "not found" in result["error"]

    def test_get_existing_invoice(self, loaded_session):
        # First get an invoice number from the query tool
        qr = query_invoices(loaded_session, limit=1)
        inv_no = qr["invoices"][0]["invoice_no"]

        result = get_invoice(loaded_session, invoice_no=inv_no)
        assert "error" not in result
        assert result["invoice_no"] == inv_no

    def test_header_fields(self, loaded_session):
        qr = query_invoices(loaded_session, limit=1)
        inv_no = qr["invoices"][0]["invoice_no"]

        result = get_invoice(loaded_session, invoice_no=inv_no)
        assert "invoice_no" in result
        assert "invoice_date" in result
        assert "invoice_type" in result
        assert "atcud" in result
        assert "hash" in result
        assert "status" in result
        assert "status_date" in result
        assert "source_billing" in result
        assert "system_entry_date" in result
        assert "customer_id" in result
        assert "customer_name" in result
        assert "customer_nif" in result

    def test_document_totals(self, loaded_session):
        qr = query_invoices(loaded_session, limit=1)
        inv_no = qr["invoices"][0]["invoice_no"]

        result = get_invoice(loaded_session, invoice_no=inv_no)
        totals = result["document_totals"]
        assert "net_total" in totals
        assert "tax_payable" in totals
        assert "gross_total" in totals
        # Gross should equal net + tax
        gross = Decimal(totals["gross_total"])
        net = Decimal(totals["net_total"])
        tax = Decimal(totals["tax_payable"])
        assert gross == net + tax

    def test_special_regimes(self, loaded_session):
        qr = query_invoices(loaded_session, limit=1)
        inv_no = qr["invoices"][0]["invoice_no"]

        result = get_invoice(loaded_session, invoice_no=inv_no)
        sr = result["special_regimes"]
        assert "self_billing_indicator" in sr
        assert "cash_vat_scheme_indicator" in sr
        assert "third_parties_billing_indicator" in sr

    def test_lines_present(self, loaded_session):
        qr = query_invoices(loaded_session, limit=1)
        inv_no = qr["invoices"][0]["invoice_no"]

        result = get_invoice(loaded_session, invoice_no=inv_no)
        assert "lines" in result
        assert "line_count" in result
        assert result["line_count"] > 0
        assert len(result["lines"]) == result["line_count"]

    def test_line_structure(self, loaded_session):
        qr = query_invoices(loaded_session, limit=1)
        inv_no = qr["invoices"][0]["invoice_no"]

        result = get_invoice(loaded_session, invoice_no=inv_no)
        line = result["lines"][0]
        assert "line_number" in line
        assert "product_code" in line
        assert "product_description" in line
        assert "quantity" in line
        assert "unit_of_measure" in line
        assert "unit_price" in line
        assert "credit_amount" in line
        assert "debit_amount" in line
        assert "tax" in line
        assert "tax_type" in line["tax"]
        assert "tax_country_region" in line["tax"]
        assert "tax_code" in line["tax"]
        assert "tax_percentage" in line["tax"]

    def test_credit_note_has_references(self, loaded_session):
        # Find a credit note
        qr = query_invoices(loaded_session, doc_type="NC", limit=5)
        if qr["total_count"] == 0:
            pytest.skip("No credit notes in data")

        # Check if any NC has references on its lines
        found_ref = False
        for inv_summary in qr["invoices"]:
            result = get_invoice(loaded_session, invoice_no=inv_summary["invoice_no"])
            for line in result["lines"]:
                if "references" in line:
                    found_ref = True
                    assert "reference" in line["references"]
                    assert "reason" in line["references"]
                    break
            if found_ref:
                break
        # Not all credit notes have references, so just check structure if found

    def test_line_count_matches_query(self, loaded_session):
        """Line count from get_invoice should match line_count from query_invoices."""
        qr = query_invoices(loaded_session, limit=5)
        for inv_summary in qr["invoices"]:
            detail = get_invoice(loaded_session, invoice_no=inv_summary["invoice_no"])
            assert detail["line_count"] == inv_summary["line_count"]
