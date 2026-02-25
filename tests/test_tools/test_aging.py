"""Tests for the saft_aging tool."""

from decimal import Decimal
from pathlib import Path

import pytest

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.state import SessionState
from saft_mcp.tools.aging import aging_analysis

REAL_DATA_DIR = Path(__file__).parent.parent.parent / "Saft Josefinas 2025"
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"


@pytest.fixture(scope="module")
def loaded_session():
    if not REAL_FULL_YEAR.exists():
        pytest.skip("Real SAF-T files not available")
    session = SessionState()
    session.loaded_file = parse_saft_file(str(REAL_FULL_YEAR))
    return session


class TestAging:
    def test_no_file_loaded(self):
        session = SessionState()
        result = aging_analysis(session)
        assert "error" in result

    def test_basic_aging(self, loaded_session):
        result = aging_analysis(loaded_session, reference_date="2025-12-31")
        assert "reference_date" in result
        assert "buckets" in result
        assert "customer_count" in result
        assert "customers" in result
        assert "totals" in result
        assert result["reference_date"] == "2025-12-31"

    def test_default_buckets(self, loaded_session):
        result = aging_analysis(loaded_session, reference_date="2025-12-31")
        assert result["buckets"] == ["0-30", "31-60", "61-90", "91-120", ">120"]

    def test_custom_buckets(self, loaded_session):
        result = aging_analysis(loaded_session, reference_date="2025-12-31", buckets=[15, 30, 60])
        assert result["buckets"] == ["0-15", "16-30", "31-60", ">60"]

    def test_customer_structure(self, loaded_session):
        result = aging_analysis(loaded_session, reference_date="2025-12-31")
        if result["customer_count"] > 0:
            cust = result["customers"][0]
            assert "customer_id" in cust
            assert "customer_name" in cust
            assert "total_outstanding" in cust
            # Should have bucket columns
            for bucket in result["buckets"]:
                assert bucket in cust

    def test_totals_row(self, loaded_session):
        result = aging_analysis(loaded_session, reference_date="2025-12-31")
        totals = result["totals"]
        assert totals["customer_id"] == "TOTAL"
        for bucket in result["buckets"]:
            assert bucket in totals

    def test_sorted_by_outstanding(self, loaded_session):
        result = aging_analysis(loaded_session, reference_date="2025-12-31")
        if result["customer_count"] > 1:
            amounts = [Decimal(c["total_outstanding"]) for c in result["customers"]]
            assert amounts == sorted(amounts, reverse=True)

    def test_outstanding_is_positive(self, loaded_session):
        result = aging_analysis(loaded_session, reference_date="2025-12-31")
        for cust in result["customers"]:
            assert Decimal(cust["total_outstanding"]) > 0
