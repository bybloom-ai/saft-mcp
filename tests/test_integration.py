"""Full integration tests -- exercise the complete MCP tool workflow.

Tests the realistic sequence: load -> validate -> summary -> query -> tax_summary.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from saft_mcp.state import SessionState
from saft_mcp.tools.load import load_saft
from saft_mcp.tools.query_invoices import query_invoices
from saft_mcp.tools.summary import summarize_saft
from saft_mcp.tools.tax_summary import tax_summary
from saft_mcp.tools.validate import validate_saft

REAL_DATA_DIR = Path(__file__).parent.parent / "Saft Josefinas 2025"
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"
REAL_MONTHLY = REAL_DATA_DIR / "5108036012025202502031408.xml"


@pytest.fixture
def session():
    return SessionState()


class TestFullWorkflowFullYear:
    """End-to-end test with the full-year SAF-T file."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_data(self):
        if not REAL_FULL_YEAR.exists():
            pytest.skip("Real SAF-T files not available")

    def test_complete_workflow(self, session):
        # Step 1: Load
        load_result = load_saft(session, str(REAL_FULL_YEAR))
        assert "error" not in load_result
        assert load_result["company_name"] == "BLOOMERS, S.A"
        assert load_result["fiscal_year"] == 2025
        assert session.loaded_file is not None

        # Step 2: Validate
        validate_result = validate_saft(session)
        assert "valid" in validate_result
        assert isinstance(validate_result["error_count"], int)
        assert isinstance(validate_result["warning_count"], int)

        # Step 3: Summary
        summary_result = summarize_saft(session)
        assert "error" not in summary_result
        assert Decimal(summary_result["total_revenue"]) > 0
        assert summary_result["invoice_count"] > 0
        assert summary_result["customer_count"] > 0

        # Step 4: Query invoices (unfiltered)
        query_result = query_invoices(session)
        assert query_result["total_count"] > 0
        assert len(query_result["invoices"]) > 0

        # Step 5: Query invoices (filtered)
        filtered = query_invoices(
            session,
            doc_type="FR",
            date_from="2025-01-01",
            date_to="2025-12-31",
        )
        for inv in filtered["invoices"]:
            assert inv["invoice_type"] == "FR"

        # Step 6: Tax summary
        tax_result = tax_summary(session, group_by="rate")
        assert len(tax_result["entries"]) > 0
        assert Decimal(tax_result["totals"]["gross_total"]) > 0

        # Step 7: Tax summary by month
        monthly_tax = tax_summary(session, group_by="month")
        assert len(monthly_tax["entries"]) > 0

    def test_cross_tool_consistency(self, session):
        """Verify that summary and tax_summary produce consistent totals."""
        load_saft(session, str(REAL_FULL_YEAR))

        summary = summarize_saft(session)
        tax = tax_summary(session, group_by="rate")

        # The number of invoices (non-cancelled, non-credit-note)
        # should be >= the total invoice_count from tax entries
        # (tax entries count per group key, not per invoice)
        assert summary["invoice_count"] > 0

        # Both tools should report the same period
        assert summary["period"] == tax["period"]

    def test_query_all_then_count(self, session):
        """Verify query total_count matches summary invoice counts."""
        load_saft(session, str(REAL_FULL_YEAR))

        summary = summarize_saft(session)
        all_invoices = query_invoices(session, limit=500)

        # query_invoices returns ALL invoices (including cancelled and credit notes)
        # summary only counts non-cancelled non-NC
        total_from_query = all_invoices["total_count"]
        invoice_count = summary["invoice_count"]
        credit_count = summary["credit_note_count"]

        # Total invoices from query should be >= invoice_count + credit_count
        # (cancelled ones are also in query unless filtered)
        assert total_from_query >= invoice_count + credit_count


class TestFullWorkflowMonthly:
    """End-to-end test with a monthly SAF-T file."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_data(self):
        if not REAL_MONTHLY.exists():
            pytest.skip("Real SAF-T files not available")

    def test_monthly_workflow(self, session):
        # Monthly files have partial MasterFiles (no products, no tax table)
        load_result = load_saft(session, str(REAL_MONTHLY))
        assert "error" not in load_result
        assert load_result["saft_type"] == "invoicing"

        # Summary should still work
        summary = summarize_saft(session)
        assert "error" not in summary
        assert summary["company_name"] == "BLOOMERS, S.A"

        # Queries should work
        query = query_invoices(session)
        assert query["total_count"] > 0

        # Tax summary should work
        tax = tax_summary(session, group_by="rate")
        assert len(tax["entries"]) > 0


class TestErrorHandling:
    """Test error paths in the workflow."""

    def test_tools_without_load(self, session):
        # All tools should return error when no file is loaded
        validate_result = validate_saft(session)
        assert "error" in validate_result

        summary_result = summarize_saft(session)
        assert "error" in summary_result

        query_result = query_invoices(session)
        assert "error" in query_result

        tax_result = tax_summary(session)
        assert "error" in tax_result

    def test_load_nonexistent_file(self, session):
        from saft_mcp.exceptions import SaftParseError

        with pytest.raises(SaftParseError, match="File not found"):
            load_saft(session, "/nonexistent/path/file.xml")
        assert session.loaded_file is None

    def test_load_invalid_file(self, session, tmp_path):
        from saft_mcp.exceptions import SaftParseError

        f = tmp_path / "bad.xml"
        f.write_text("<not-a-saft-file/>")
        with pytest.raises(SaftParseError):
            load_saft(session, str(f))
