"""Tests for the saft_tax_summary tool."""

from decimal import Decimal
from pathlib import Path

import pytest

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.state import SessionState
from saft_mcp.tools.tax_summary import tax_summary

REAL_DATA_DIR = Path(__file__).parent.parent.parent / "Saft Josefinas 2025"
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"


@pytest.fixture(scope="module")
def loaded_session():
    if not REAL_FULL_YEAR.exists():
        pytest.skip("Real SAF-T files not available")
    session = SessionState()
    session.loaded_file = parse_saft_file(str(REAL_FULL_YEAR))
    return session


class TestTaxSummary:
    def test_no_file_loaded(self):
        session = SessionState()
        result = tax_summary(session)
        assert "error" in result

    def test_group_by_rate(self, loaded_session):
        result = tax_summary(loaded_session, group_by="rate")
        assert result["group_by"] == "rate"
        assert "entries" in result
        assert "totals" in result
        assert len(result["entries"]) > 0
        # Each entry key should end with %
        for entry in result["entries"]:
            assert entry["group_key"].endswith("%")
            assert "tax_percentage" in entry
            assert "taxable_base" in entry
            assert "tax_amount" in entry
            assert "gross_total" in entry
            assert "invoice_count" in entry

    def test_group_by_month(self, loaded_session):
        result = tax_summary(loaded_session, group_by="month")
        assert result["group_by"] == "month"
        for entry in result["entries"]:
            # Month keys should be YYYY-MM
            assert len(entry["group_key"]) == 7
            assert entry["group_key"][4] == "-"

    def test_group_by_doc_type(self, loaded_session):
        result = tax_summary(loaded_session, group_by="doc_type")
        assert result["group_by"] == "doc_type"
        for entry in result["entries"]:
            assert entry["group_key"] in ("FT", "FR", "NC", "ND", "FS")

    def test_totals_match_entries(self, loaded_session):
        result = tax_summary(loaded_session, group_by="rate")
        total_base = sum(Decimal(e["taxable_base"]) for e in result["entries"])
        total_tax = sum(Decimal(e["tax_amount"]) for e in result["entries"])
        total_gross = sum(Decimal(e["gross_total"]) for e in result["entries"])

        assert Decimal(result["totals"]["taxable_base"]) == total_base
        assert Decimal(result["totals"]["tax_amount"]) == total_tax
        assert Decimal(result["totals"]["gross_total"]) == total_gross

    def test_date_filter(self, loaded_session):
        full = tax_summary(loaded_session, group_by="rate")
        filtered = tax_summary(
            loaded_session,
            date_from="2025-06-01",
            date_to="2025-06-30",
            group_by="rate",
        )
        # Filtered should have less or equal total
        full_gross = Decimal(full["totals"]["gross_total"])
        filtered_gross = Decimal(filtered["totals"]["gross_total"])
        assert filtered_gross <= full_gross

    def test_period_field(self, loaded_session):
        result = tax_summary(loaded_session)
        assert result["period"] == "2025"

    def test_tax_amounts_consistent(self, loaded_session):
        result = tax_summary(loaded_session, group_by="rate")
        for entry in result["entries"]:
            base = Decimal(entry["taxable_base"])
            tax = Decimal(entry["tax_amount"])
            gross = Decimal(entry["gross_total"])
            # gross should equal base + tax
            assert gross == base + tax, (
                f"For {entry['group_key']}: {base} + {tax} != {gross}"
            )
