"""Tests for the saft_query_invoices tool."""

from decimal import Decimal
from pathlib import Path

import pytest

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.state import SessionState
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


class TestQueryInvoices:
    def test_no_file_loaded(self):
        session = SessionState()
        result = query_invoices(session)
        assert "error" in result

    def test_unfiltered_query(self, loaded_session):
        result = query_invoices(loaded_session)
        assert "total_count" in result
        assert "returned_count" in result
        assert "offset" in result
        assert "has_more" in result
        assert "invoices" in result
        assert result["total_count"] > 0
        assert result["returned_count"] > 0
        assert result["returned_count"] <= 50  # default limit

    def test_invoice_structure(self, loaded_session):
        result = query_invoices(loaded_session)
        inv = result["invoices"][0]
        assert "invoice_no" in inv
        assert "invoice_date" in inv
        assert "invoice_type" in inv
        assert "customer_id" in inv
        assert "customer_name" in inv
        assert "net_total" in inv
        assert "tax_payable" in inv
        assert "gross_total" in inv
        assert "status" in inv
        assert "line_count" in inv

    def test_filter_by_doc_type(self, loaded_session):
        result = query_invoices(loaded_session, doc_type="FR")
        for inv in result["invoices"]:
            assert inv["invoice_type"] == "FR"

    def test_filter_by_status_cancelled(self, loaded_session):
        result = query_invoices(loaded_session, status="A")
        for inv in result["invoices"]:
            assert inv["status"] == "A"

    def test_filter_by_date_range(self, loaded_session):
        result = query_invoices(
            loaded_session,
            date_from="2025-06-01",
            date_to="2025-06-30",
        )
        for inv in result["invoices"]:
            assert inv["invoice_date"] >= "2025-06-01"
            assert inv["invoice_date"] <= "2025-06-30"

    def test_filter_by_min_amount(self, loaded_session):
        result = query_invoices(loaded_session, min_amount=1000.0)
        for inv in result["invoices"]:
            assert Decimal(inv["gross_total"]) >= 1000

    def test_filter_by_max_amount(self, loaded_session):
        result = query_invoices(loaded_session, max_amount=50.0)
        for inv in result["invoices"]:
            assert Decimal(inv["gross_total"]) <= 50

    def test_filter_by_customer_name(self, loaded_session):
        # Use a partial match -- first get a customer name from the data
        all_invs = query_invoices(loaded_session, limit=1)
        if all_invs["total_count"] == 0:
            pytest.skip("No invoices")
        name_fragment = all_invs["invoices"][0]["customer_name"][:5]
        result = query_invoices(loaded_session, customer_name=name_fragment)
        assert result["total_count"] > 0
        for inv in result["invoices"]:
            assert name_fragment.lower() in inv["customer_name"].lower()

    def test_pagination(self, loaded_session):
        # Get first page
        page1 = query_invoices(loaded_session, limit=5, offset=0)
        assert page1["returned_count"] <= 5

        if page1["has_more"]:
            # Get second page
            page2 = query_invoices(loaded_session, limit=5, offset=5)
            assert page2["returned_count"] <= 5
            # Should be different invoices
            ids1 = {inv["invoice_no"] for inv in page1["invoices"]}
            ids2 = {inv["invoice_no"] for inv in page2["invoices"]}
            assert ids1.isdisjoint(ids2)

    def test_limit_capped_at_max(self, loaded_session):
        result = query_invoices(loaded_session, limit=9999)
        assert result["returned_count"] <= 500  # max_query_limit

    def test_combined_filters(self, loaded_session):
        result = query_invoices(
            loaded_session,
            date_from="2025-01-01",
            date_to="2025-12-31",
            doc_type="FR",
            min_amount=10.0,
        )
        for inv in result["invoices"]:
            assert inv["invoice_type"] == "FR"
            assert inv["invoice_date"] >= "2025-01-01"
            assert Decimal(inv["gross_total"]) >= 10
