"""Tests for the saft_load tool."""

import os
from pathlib import Path

import pytest

from saft_mcp.state import SessionState
from saft_mcp.tools.load import load_saft, validate_file_path

REAL_DATA_DIR = Path(__file__).parent.parent.parent / "Saft Josefinas 2025"
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"
REAL_MONTHLY = REAL_DATA_DIR / "5108036012025202502031408.xml"


class TestValidateFilePath:
    def test_nonexistent_file(self):
        with pytest.raises(Exception, match="File not found"):
            validate_file_path("/nonexistent/file.xml")

    def test_directory_not_file(self, tmp_path):
        with pytest.raises(Exception, match="not a file"):
            validate_file_path(str(tmp_path))

    def test_wrong_extension(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        with pytest.raises(Exception, match="Unsupported file type"):
            validate_file_path(str(f))

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.xml"
        f.write_text("")
        with pytest.raises(Exception, match="empty"):
            validate_file_path(str(f))

    def test_valid_file(self):
        if not REAL_FULL_YEAR.exists():
            pytest.skip("Real SAF-T files not available")
        result = validate_file_path(str(REAL_FULL_YEAR))
        assert os.path.isabs(result)


class TestLoadSaft:
    def test_load_full_year(self):
        if not REAL_FULL_YEAR.exists():
            pytest.skip("Real SAF-T files not available")

        session = SessionState()
        result = load_saft(session, str(REAL_FULL_YEAR))

        assert "error" not in result
        assert result["company_name"] == "BLOOMERS, S.A"
        assert result["tax_registration_number"] == "510803601"
        assert result["fiscal_year"] == 2025
        assert result["period"] == "2025"
        assert result["saft_type"] == "invoicing"
        assert result["saft_version"] == "1.04_01"
        assert result["parse_mode"] == "full"
        assert "record_counts" in result
        assert result["record_counts"]["invoices"] > 0
        assert result["record_counts"]["customers"] > 0
        assert result["file_size_mb"] > 0

        # Session should be populated
        assert session.loaded_file is not None
        assert session.file_path is not None
        assert session.parse_mode == "full"

    def test_load_monthly(self):
        if not REAL_MONTHLY.exists():
            pytest.skip("Real SAF-T files not available")

        session = SessionState()
        result = load_saft(session, str(REAL_MONTHLY))

        assert "error" not in result
        assert result["company_name"] == "BLOOMERS, S.A"
        assert result["saft_type"] == "invoicing"
        # Monthly file should have a month-based period
        assert "2025-" in result["period"] or "to" in result["period"]

    def test_load_replaces_previous(self):
        if not REAL_FULL_YEAR.exists():
            pytest.skip("Real SAF-T files not available")

        session = SessionState()
        load_saft(session, str(REAL_FULL_YEAR))
        first_data = session.loaded_file

        # Load again should replace
        load_saft(session, str(REAL_FULL_YEAR))
        assert session.loaded_file is not None
        # It's a new parse, different object
        assert session.loaded_file is not first_data
