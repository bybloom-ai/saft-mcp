"""Tests for the saft_export tool."""

import csv
import tempfile
from pathlib import Path

import pytest

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.state import SessionState
from saft_mcp.tools.export import export_csv

REAL_DATA_DIR = Path(__file__).parent.parent.parent / "Saft Josefinas 2025"
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"


@pytest.fixture(scope="module")
def loaded_session():
    if not REAL_FULL_YEAR.exists():
        pytest.skip("Real SAF-T files not available")
    session = SessionState()
    session.loaded_file = parse_saft_file(str(REAL_FULL_YEAR))
    return session


class TestExport:
    def test_no_file_loaded(self):
        session = SessionState()
        with tempfile.NamedTemporaryFile(suffix=".csv") as f:
            result = export_csv(session, export_type="invoices", file_path=f.name)
        assert "error" in result

    def test_invalid_export_type(self, loaded_session):
        with tempfile.NamedTemporaryFile(suffix=".csv") as f:
            result = export_csv(loaded_session, export_type="invalid", file_path=f.name)
        assert "error" in result

    def test_export_invoices(self, loaded_session):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        result = export_csv(loaded_session, export_type="invoices", file_path=path)
        assert "error" not in result
        assert result["row_count"] > 0
        assert "invoice_no" in result["columns"]
        # Verify CSV is readable
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == result["row_count"]
        Path(path).unlink()

    def test_export_customers(self, loaded_session):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        result = export_csv(loaded_session, export_type="customers", file_path=path)
        assert "error" not in result
        assert result["row_count"] > 0
        assert "customer_id" in result["columns"]
        assert "company_name" in result["columns"]
        Path(path).unlink()

    def test_export_products(self, loaded_session):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        result = export_csv(loaded_session, export_type="products", file_path=path)
        assert "error" not in result
        assert result["row_count"] > 0
        assert "product_code" in result["columns"]
        Path(path).unlink()

    def test_export_tax_summary(self, loaded_session):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        result = export_csv(loaded_session, export_type="tax_summary", file_path=path)
        assert "error" not in result
        assert result["row_count"] > 0
        assert "taxable_base" in result["columns"]
        Path(path).unlink()

    def test_export_anomalies(self, loaded_session):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        result = export_csv(loaded_session, export_type="anomalies", file_path=path)
        assert "error" not in result
        assert "type" in result["columns"]
        Path(path).unlink()

    def test_export_with_filters(self, loaded_session):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        result = export_csv(
            loaded_session,
            export_type="invoices",
            file_path=path,
            filters={"doc_type": "NC"},
        )
        assert "error" not in result
        # Should only have credit notes
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                assert row["invoice_type"] == "NC"
        Path(path).unlink()
