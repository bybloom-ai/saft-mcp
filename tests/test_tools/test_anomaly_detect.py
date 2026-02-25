"""Tests for the saft_anomaly_detect tool."""

from pathlib import Path

import pytest

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.state import SessionState
from saft_mcp.tools.anomaly_detect import detect_anomalies

REAL_DATA_DIR = Path(__file__).parent.parent.parent / "Saft Josefinas 2025"
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"


@pytest.fixture(scope="module")
def loaded_session():
    if not REAL_FULL_YEAR.exists():
        pytest.skip("Real SAF-T files not available")
    session = SessionState()
    session.loaded_file = parse_saft_file(str(REAL_FULL_YEAR))
    return session


class TestAnomalyDetect:
    def test_no_file_loaded(self):
        session = SessionState()
        result = detect_anomalies(session)
        assert "error" in result

    def test_all_checks(self, loaded_session):
        result = detect_anomalies(loaded_session)
        assert "checks_run" in result
        assert "anomaly_count" in result
        assert "anomalies" in result
        assert len(result["checks_run"]) == 6

    def test_anomaly_structure(self, loaded_session):
        result = detect_anomalies(loaded_session)
        if result["anomaly_count"] > 0:
            anomaly = result["anomalies"][0]
            assert "type" in anomaly
            assert "severity" in anomaly
            assert "description" in anomaly
            assert "affected_documents" in anomaly
            assert anomaly["severity"] in ("warning", "info")

    def test_single_check(self, loaded_session):
        result = detect_anomalies(loaded_session, checks=["weekend_invoices"])
        assert result["checks_run"] == ["weekend_invoices"]
        for a in result["anomalies"]:
            assert a["type"] == "weekend_invoices"

    def test_multiple_checks(self, loaded_session):
        result = detect_anomalies(loaded_session, checks=["zero_amount", "duplicate_invoices"])
        assert len(result["checks_run"]) == 2
        for a in result["anomalies"]:
            assert a["type"] in ("zero_amount", "duplicate_invoices")

    def test_zero_amount_check(self, loaded_session):
        """We know NC 2025A17/2 has gross_total 0.00 from earlier analysis."""
        result = detect_anomalies(loaded_session, checks=["zero_amount"])
        if result["anomaly_count"] > 0:
            docs = result["anomalies"][0]["affected_documents"]
            assert any("NC" in d for d in docs)

    def test_numbering_gaps_check(self, loaded_session):
        result = detect_anomalies(loaded_session, checks=["numbering_gaps"])
        # Should run without error; gaps may or may not exist
        assert result["checks_run"] == ["numbering_gaps"]

    def test_cancelled_ratio_check(self, loaded_session):
        result = detect_anomalies(loaded_session, checks=["cancelled_ratio"])
        assert result["checks_run"] == ["cancelled_ratio"]
