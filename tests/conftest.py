"""Shared fixtures for SAF-T MCP tests."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
REAL_DATA_DIR = Path(__file__).parent.parent / "Saft Josefinas 2025"

# Real SAF-T files (only available locally, skip if missing)
REAL_FULL_YEAR = REAL_DATA_DIR / "5108036012025_Completo.xml"
REAL_MONTHLY = REAL_DATA_DIR / "5108036012025202502031408.xml"


@pytest.fixture
def real_full_year_path() -> Path:
    if not REAL_FULL_YEAR.exists():
        pytest.skip("Real SAF-T files not available")
    return REAL_FULL_YEAR


@pytest.fixture
def real_monthly_path() -> Path:
    if not REAL_MONTHLY.exists():
        pytest.skip("Real SAF-T files not available")
    return REAL_MONTHLY
