"""Tests for the saft_validate tool."""

from pathlib import Path

import pytest

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.state import SessionState
from saft_mcp.tools.validate import validate_saft

REAL_DATA_DIR = Path(__file__).parent.parent.parent / "Saft Josefinas 2025"
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"


@pytest.fixture(scope="module")
def loaded_session():
    if not REAL_FULL_YEAR.exists():
        pytest.skip("Real SAF-T files not available")
    session = SessionState()
    session.loaded_file = parse_saft_file(str(REAL_FULL_YEAR))
    session.file_path = str(REAL_FULL_YEAR)
    return session


class TestValidateSaft:
    def test_no_file_loaded(self):
        session = SessionState()
        result = validate_saft(session)
        assert "error" in result

    def test_all_rules(self, loaded_session):
        result = validate_saft(loaded_session)
        assert "valid" in result
        assert "error_count" in result
        assert "warning_count" in result
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_xsd_only(self, loaded_session):
        result = validate_saft(loaded_session, rules=["xsd"])
        assert "valid" in result
        # All results should be xsd-related
        for r in result["results"]:
            assert r["rule"] == "xsd"

    def test_nif_only(self, loaded_session):
        result = validate_saft(loaded_session, rules=["nif"])
        assert "valid" in result
        for r in result["results"]:
            assert r["rule"] == "nif"

    def test_hash_chain_only(self, loaded_session):
        result = validate_saft(loaded_session, rules=["hash_chain"])
        assert "valid" in result

    def test_control_totals(self, loaded_session):
        result = validate_saft(loaded_session, rules=["control_totals"])
        assert "valid" in result
        # Real data should have matching control totals
        ctrl_errors = [r for r in result["results"] if r["rule"] == "control_totals"]
        assert len(ctrl_errors) == 0, f"Control total errors: {ctrl_errors}"

    def test_result_structure(self, loaded_session):
        result = validate_saft(loaded_session)
        for r in result["results"]:
            assert "severity" in r
            assert "rule" in r
            assert "location" in r
            assert "message" in r
