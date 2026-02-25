"""Tests for the saft_compare tool."""

from decimal import Decimal
from pathlib import Path

import pytest

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.state import SessionState
from saft_mcp.tools.compare import compare_saft

REAL_DATA_DIR = Path(__file__).parent.parent.parent / "Saft Josefinas 2025"
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"
REAL_MONTHLY = REAL_DATA_DIR / "5108036012025202502031408.xml"


@pytest.fixture(scope="module")
def loaded_session():
    if not REAL_FULL_YEAR.exists():
        pytest.skip("Real SAF-T files not available")
    session = SessionState()
    session.loaded_file = parse_saft_file(str(REAL_FULL_YEAR))
    return session


class TestCompare:
    def test_no_file_loaded(self):
        session = SessionState()
        result = compare_saft(session, file_path="dummy.xml")
        assert "error" in result

    def test_invalid_comparison_file(self, loaded_session):
        result = compare_saft(loaded_session, file_path="/nonexistent/file.xml")
        assert "error" in result

    def test_compare_full_vs_monthly(self, loaded_session):
        if not REAL_MONTHLY.exists():
            pytest.skip("Monthly SAF-T file not available")
        result = compare_saft(loaded_session, file_path=str(REAL_MONTHLY))
        assert "period_a" in result
        assert "period_b" in result
        assert "changes" in result
        assert "metrics_compared" in result

    def test_compare_revenue_metric(self, loaded_session):
        if not REAL_MONTHLY.exists():
            pytest.skip("Monthly SAF-T file not available")
        result = compare_saft(loaded_session, file_path=str(REAL_MONTHLY), metrics=["revenue"])
        assert result["metrics_compared"] == ["revenue"]
        rev = result["changes"]["revenue"]
        assert "gross_revenue" in rev
        assert "credit_notes" in rev
        assert "net_revenue" in rev
        for key in ["gross_revenue", "credit_notes", "net_revenue"]:
            assert "file_a" in rev[key]
            assert "file_b" in rev[key]
            assert "delta" in rev[key]
            assert "delta_pct" in rev[key]

    def test_compare_customers_metric(self, loaded_session):
        if not REAL_MONTHLY.exists():
            pytest.skip("Monthly SAF-T file not available")
        result = compare_saft(loaded_session, file_path=str(REAL_MONTHLY), metrics=["customers"])
        custs = result["changes"]["customers"]
        assert "count_a" in custs
        assert "count_b" in custs
        assert "new_customers" in custs
        assert "lost_customers" in custs

    def test_compare_doc_types_metric(self, loaded_session):
        if not REAL_MONTHLY.exists():
            pytest.skip("Monthly SAF-T file not available")
        result = compare_saft(loaded_session, file_path=str(REAL_MONTHLY), metrics=["doc_types"])
        dt = result["changes"]["doc_types"]
        # Should have at least FR entries
        assert len(dt) > 0
        for doc_type, vals in dt.items():
            assert "file_a" in vals
            assert "file_b" in vals
            assert "delta" in vals

    def test_compare_self(self, loaded_session):
        """Comparing a file to itself should show zero deltas."""
        result = compare_saft(loaded_session, file_path=str(REAL_FULL_YEAR), metrics=["revenue"])
        rev = result["changes"]["revenue"]
        for key in ["gross_revenue", "credit_notes", "net_revenue"]:
            assert Decimal(rev[key]["delta"]) == 0
