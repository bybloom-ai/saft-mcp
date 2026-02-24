"""Tests for the saft_summary tool."""

from decimal import Decimal
from pathlib import Path

import pytest

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.state import SessionState
from saft_mcp.tools.summary import summarize_saft

REAL_DATA_DIR = Path(__file__).parent.parent.parent / "Saft Josefinas 2025"
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"


@pytest.fixture(scope="module")
def loaded_session():
    if not REAL_FULL_YEAR.exists():
        pytest.skip("Real SAF-T files not available")
    session = SessionState()
    session.loaded_file = parse_saft_file(str(REAL_FULL_YEAR))
    return session


class TestSummarizeSaft:
    def test_no_file_loaded(self):
        session = SessionState()
        result = summarize_saft(session)
        assert "error" in result

    def test_basic_fields(self, loaded_session):
        result = summarize_saft(loaded_session)
        assert result["company_name"] == "BLOOMERS, S.A"
        assert result["period"] == "2025"
        assert "total_revenue" in result
        assert "total_credit_notes" in result
        assert "net_revenue" in result
        assert "invoice_count" in result
        assert "credit_note_count" in result
        assert "customer_count" in result
        assert "product_count" in result

    def test_revenue_is_positive(self, loaded_session):
        result = summarize_saft(loaded_session)
        assert Decimal(result["total_revenue"]) > 0

    def test_net_revenue_calculation(self, loaded_session):
        result = summarize_saft(loaded_session)
        total = Decimal(result["total_revenue"])
        credits = Decimal(result["total_credit_notes"])
        net = Decimal(result["net_revenue"])
        assert net == total - credits

    def test_vat_breakdown_present(self, loaded_session):
        result = summarize_saft(loaded_session)
        assert isinstance(result["vat_breakdown"], list)
        assert len(result["vat_breakdown"]) > 0
        for entry in result["vat_breakdown"]:
            assert "tax_percentage" in entry
            assert "taxable_base" in entry
            assert "tax_amount" in entry

    def test_top_customers(self, loaded_session):
        result = summarize_saft(loaded_session)
        assert isinstance(result["top_customers"], list)
        assert len(result["top_customers"]) > 0
        assert len(result["top_customers"]) <= 10
        for cust in result["top_customers"]:
            assert "customer_id" in cust
            assert "customer_name" in cust
            assert "total_revenue" in cust
            assert "invoice_count" in cust

    def test_top_customers_sorted_descending(self, loaded_session):
        result = summarize_saft(loaded_session)
        revenues = [Decimal(c["total_revenue"]) for c in result["top_customers"]]
        assert revenues == sorted(revenues, reverse=True)

    def test_document_type_distribution(self, loaded_session):
        result = summarize_saft(loaded_session)
        dist = result["document_type_distribution"]
        assert isinstance(dist, dict)
        # Should have at least FT or FR invoices
        assert any(k in dist for k in ("FT", "FR")), f"Expected FT or FR in {dist}"
