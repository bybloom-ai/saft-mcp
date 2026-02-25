"""Tests for the saft_query_customers tool."""

from decimal import Decimal
from pathlib import Path

import pytest

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.state import SessionState
from saft_mcp.tools.query_customers import query_customers

REAL_DATA_DIR = Path(__file__).parent.parent.parent / "Saft Josefinas 2025"
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"


@pytest.fixture(scope="module")
def loaded_session():
    if not REAL_FULL_YEAR.exists():
        pytest.skip("Real SAF-T files not available")
    session = SessionState()
    session.loaded_file = parse_saft_file(str(REAL_FULL_YEAR))
    return session


class TestQueryCustomers:
    def test_no_file_loaded(self):
        session = SessionState()
        result = query_customers(session)
        assert "error" in result

    def test_unfiltered_query(self, loaded_session):
        result = query_customers(loaded_session)
        assert "total_count" in result
        assert "returned_count" in result
        assert "offset" in result
        assert "has_more" in result
        assert "customers" in result
        assert result["total_count"] == 113

    def test_customer_structure(self, loaded_session):
        result = query_customers(loaded_session, limit=1)
        cust = result["customers"][0]
        assert "customer_id" in cust
        assert "customer_tax_id" in cust
        assert "company_name" in cust
        assert "billing_address" in cust
        assert "address_detail" in cust["billing_address"]
        assert "city" in cust["billing_address"]
        assert "postal_code" in cust["billing_address"]
        assert "country" in cust["billing_address"]
        assert "self_billing_indicator" in cust
        assert "invoice_count" in cust
        assert "total_revenue" in cust

    def test_filter_by_name(self, loaded_session):
        result = query_customers(loaded_session, name="consumidor")
        assert result["total_count"] > 0
        for cust in result["customers"]:
            assert "consumidor" in cust["company_name"].lower()

    def test_filter_by_nif(self, loaded_session):
        # Find a customer with invoices first
        all_custs = query_customers(loaded_session, limit=5)
        target = None
        for c in all_custs["customers"]:
            if c["invoice_count"] > 0:
                target = c
                break
        if target is None:
            pytest.skip("No customers with invoices")
        nif_fragment = target["customer_tax_id"][:4]
        result = query_customers(loaded_session, nif=nif_fragment)
        assert result["total_count"] > 0
        for cust in result["customers"]:
            assert nif_fragment in cust["customer_tax_id"]

    def test_revenue_stats(self, loaded_session):
        result = query_customers(loaded_session, limit=500)
        # At least some customers should have revenue
        customers_with_revenue = [
            c for c in result["customers"] if Decimal(c["total_revenue"]) > 0
        ]
        assert len(customers_with_revenue) > 0
        # Revenue should be positive (excludes credit notes)
        for cust in customers_with_revenue:
            assert Decimal(cust["total_revenue"]) > 0
            assert cust["invoice_count"] > 0

    def test_pagination(self, loaded_session):
        page1 = query_customers(loaded_session, limit=5, offset=0)
        assert page1["returned_count"] <= 5
        if page1["has_more"]:
            page2 = query_customers(loaded_session, limit=5, offset=5)
            ids1 = {c["customer_id"] for c in page1["customers"]}
            ids2 = {c["customer_id"] for c in page2["customers"]}
            assert ids1.isdisjoint(ids2)

    def test_limit_capped_at_max(self, loaded_session):
        result = query_customers(loaded_session, limit=9999)
        assert result["returned_count"] <= 500

    def test_combined_filters(self, loaded_session):
        result = query_customers(loaded_session, name="consumidor", country="PT")
        for cust in result["customers"]:
            assert "consumidor" in cust["company_name"].lower()
            assert cust["billing_address"]["country"] == "PT"
