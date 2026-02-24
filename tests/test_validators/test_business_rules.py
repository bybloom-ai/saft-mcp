"""Tests for business rules validation against real SAF-T data."""

from pathlib import Path

import pytest

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.validators.business_rules import (
    run_all_business_rules,
    validate_atcud,
    validate_control_totals,
    validate_nifs,
    validate_numbering,
    validate_tax_codes,
)

REAL_DATA_DIR = Path(__file__).parent.parent.parent / "Saft Josefinas 2025"
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"


@pytest.fixture(scope="module")
def saft_data():
    if not REAL_FULL_YEAR.exists():
        pytest.skip("Real SAF-T files not available")
    return parse_saft_file(str(REAL_FULL_YEAR))


class TestValidateNifs:
    def test_company_nif_valid(self, saft_data):
        results = validate_nifs(saft_data)
        company_errors = [r for r in results if "Header" in r.location]
        assert len(company_errors) == 0, "Company NIF should be valid"

    def test_returns_validation_results(self, saft_data):
        results = validate_nifs(saft_data)
        for r in results:
            assert r.severity in ("error", "warning")
            assert r.rule == "nif"


class TestValidateNumbering:
    def test_returns_results(self, saft_data):
        results = validate_numbering(saft_data)
        for r in results:
            assert r.severity == "error"
            assert r.rule == "numbering"


class TestValidateAtcud:
    def test_all_invoices_have_atcud(self, saft_data):
        results = validate_atcud(saft_data)
        # Post-2023 data: any missing ATCUD is an error
        missing = [r for r in results if "Missing ATCUD" in r.message]
        # Real data should have ATCUDs on all invoices
        assert len(missing) == 0, f"Found {len(missing)} invoices without ATCUD"

    def test_atcud_format_valid(self, saft_data):
        results = validate_atcud(saft_data)
        format_errors = [r for r in results if "format invalid" in r.message]
        assert len(format_errors) == 0, f"Found {len(format_errors)} invalid ATCUD formats"


class TestValidateTaxCodes:
    def test_known_tax_codes(self, saft_data):
        results = validate_tax_codes(saft_data)
        unknown = [r for r in results if "Unknown tax code" in r.message]
        assert len(unknown) == 0, f"Found {len(unknown)} unknown tax codes"


class TestValidateControlTotals:
    def test_invoice_count_matches(self, saft_data):
        results = validate_control_totals(saft_data)
        count_errors = [r for r in results if "entries" in r.message.lower()]
        assert len(count_errors) == 0, (
            f"Control total mismatch: {[r.message for r in count_errors]}"
        )


class TestRunAllBusinessRules:
    def test_returns_list(self, saft_data):
        results = run_all_business_rules(saft_data)
        assert isinstance(results, list)

    def test_all_results_have_to_dict(self, saft_data):
        results = run_all_business_rules(saft_data)
        for r in results:
            d = r.to_dict()
            assert "severity" in d
            assert "rule" in d
            assert "location" in d
            assert "message" in d
