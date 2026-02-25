"""Tests for the saft_stats tool."""

from pathlib import Path

import pytest

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.state import SessionState
from saft_mcp.tools.stats import compute_stats

REAL_DATA_DIR = Path(__file__).parent.parent.parent / "Saft Josefinas 2025"
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"


@pytest.fixture(scope="module")
def loaded_session():
    if not REAL_FULL_YEAR.exists():
        pytest.skip("Real SAF-T files not available")
    session = SessionState()
    session.loaded_file = parse_saft_file(str(REAL_FULL_YEAR))
    return session


class TestStats:
    def test_no_file_loaded(self):
        session = SessionState()
        result = compute_stats(session)
        assert "error" in result

    def test_basic_stats(self, loaded_session):
        result = compute_stats(loaded_session)
        assert "invoice_stats" in result
        assert "daily_stats" in result
        assert "weekday_distribution" in result
        assert "monthly_distribution" in result
        assert "customer_concentration" in result
        assert "top_invoice" in result
        assert "bottom_invoice" in result

    def test_invoice_stats_fields(self, loaded_session):
        result = compute_stats(loaded_session)
        stats = result["invoice_stats"]
        assert "count" in stats
        assert "mean" in stats
        assert "median" in stats
        assert "min" in stats
        assert "max" in stats
        assert "std_deviation" in stats
        assert stats["count"] > 0
        assert stats["mean"] > 0
        assert stats["max"] >= stats["min"]
        assert stats["median"] > 0

    def test_daily_stats(self, loaded_session):
        result = compute_stats(loaded_session)
        daily = result["daily_stats"]
        assert "avg_per_day" in daily
        assert "busiest_day" in daily
        assert "quietest_day" in daily
        assert "active_days" in daily
        assert daily["busiest_day"]["count"] >= daily["quietest_day"]["count"]

    def test_weekday_distribution(self, loaded_session):
        result = compute_stats(loaded_session)
        weekdays = result["weekday_distribution"]
        assert len(weekdays) == 7
        assert weekdays[0]["weekday"] == "Monday"
        assert weekdays[6]["weekday"] == "Sunday"
        total = sum(d["count"] for d in weekdays)
        assert total == result["invoice_stats"]["count"]

    def test_monthly_distribution(self, loaded_session):
        result = compute_stats(loaded_session)
        months = result["monthly_distribution"]
        assert len(months) > 0
        for m in months:
            assert "month" in m
            assert "count" in m
            assert "revenue" in m

    def test_customer_concentration(self, loaded_session):
        result = compute_stats(loaded_session)
        conc = result["customer_concentration"]
        assert "top_1" in conc
        assert "top_5" in conc
        assert "top_10" in conc
        assert "top_20" in conc
        # Top 1 share <= top 5 share <= top 10 share <= top 20 share
        assert conc["top_1"]["share_pct"] <= conc["top_5"]["share_pct"]
        assert conc["top_5"]["share_pct"] <= conc["top_10"]["share_pct"]
        assert conc["top_10"]["share_pct"] <= conc["top_20"]["share_pct"]

    def test_top_bottom_invoices(self, loaded_session):
        result = compute_stats(loaded_session)
        top = result["top_invoice"]
        bottom = result["bottom_invoice"]
        assert "invoice_no" in top
        assert "gross_total" in top
        assert "customer_name" in top
        assert float(top["gross_total"]) >= float(bottom["gross_total"])

    def test_date_filter(self, loaded_session):
        result = compute_stats(loaded_session, date_from="2025-07-01", date_to="2025-07-31")
        assert result["invoice_stats"]["count"] > 0
        # Monthly distribution should only have July
        months = result["monthly_distribution"]
        assert all(m["month"] == "2025-07" for m in months)

    def test_empty_filter_returns_error(self, loaded_session):
        result = compute_stats(loaded_session, date_from="2030-01-01", date_to="2030-12-31")
        assert "error" in result
