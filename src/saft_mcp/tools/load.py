"""saft_load tool -- Load and parse a SAF-T PT XML file."""

from __future__ import annotations

import os
from typing import Any

from saft_mcp.config import settings
from saft_mcp.exceptions import SaftFileTooLargeError, SaftParseError
from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.state import SessionState

ALLOWED_EXTENSIONS = {".xml"}


def validate_file_path(file_path: str) -> str:
    """Validate and normalize a SAF-T file path."""
    resolved = os.path.realpath(file_path)

    if not os.path.exists(resolved):
        raise SaftParseError(f"File not found: {file_path}")

    if not os.path.isfile(resolved):
        raise SaftParseError(f"Path is not a file: {file_path}")

    _, ext = os.path.splitext(resolved)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise SaftParseError(f"Unsupported file type: {ext}. Expected .xml")

    size = os.path.getsize(resolved)
    if size == 0:
        raise SaftParseError("File is empty (0 bytes)")

    if size > settings.max_file_size_bytes:
        raise SaftFileTooLargeError(
            f"File size {size / 1024 / 1024:.0f} MB exceeds limit of "
            f"{settings.max_file_size_bytes / 1024 / 1024:.0f} MB"
        )

    return resolved


def load_saft(session: SessionState, file_path: str) -> dict[str, Any]:
    """Load a SAF-T file into the session.

    Returns a LoadResponse-style dict with file metadata.
    """
    resolved = validate_file_path(file_path)
    file_size = os.path.getsize(resolved)

    # For MVP, full parse only (streaming in v0.2)
    data = parse_saft_file(resolved)

    # Store in session
    session.loaded_file = data
    session.file_metadata = data.metadata
    session.file_path = resolved
    session.parse_mode = "full"

    # Build period string
    sd = data.metadata.start_date
    ed = data.metadata.end_date
    if sd.month == 1 and ed.month == 12 and sd.day == 1 and ed.day == 31:
        period = str(data.metadata.fiscal_year)
    elif sd.month == ed.month and sd.year == ed.year:
        period = f"{sd.year}-{sd.month:02d}"
    else:
        period = f"{sd.isoformat()} to {ed.isoformat()}"

    return {
        "company_name": data.metadata.company_name,
        "tax_registration_number": data.metadata.tax_registration_number,
        "fiscal_year": data.metadata.fiscal_year,
        "period": period,
        "saft_type": data.metadata.saft_type.value,
        "saft_version": data.metadata.audit_file_version,
        "parse_mode": "full",
        "record_counts": data.metadata.record_counts,
        "file_size_mb": round(file_size / 1024 / 1024, 2),
    }
