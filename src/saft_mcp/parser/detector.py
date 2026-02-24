"""Namespace detection and file type detection for SAF-T XML files."""

import re

from saft_mcp.exceptions import SaftParseError
from saft_mcp.parser.models import SaftType

# Namespace regex -- matches any SAF-T PT namespace version
_NAMESPACE_RE = re.compile(rb'xmlns="(urn:OECD:StandardAuditFile-Tax:PT[^"]*)"')

# Known namespace -> XSD file mapping
NAMESPACE_XSD_MAP = {
    "urn:OECD:StandardAuditFile-Tax:PT_1.04_01": "saftpt1.04_01.xsd",
    "urn:OECD:StandardAuditFile-Tax:PT_1.03_01": "saftpt1.03_01.xsd",
}

# TaxAccountingBasis -> SaftType
_BASIS_TO_TYPE = {
    "C": SaftType.ACCOUNTING,
    "I": SaftType.ACCOUNTING,  # Integrated has accounting data
    "F": SaftType.INVOICING,
    "P": SaftType.INVOICING,
    "S": SaftType.INVOICING,
    "R": SaftType.INVOICING,
}


def detect_namespace(file_path: str) -> str:
    """Read the first 4 KB to extract the SAF-T namespace without parsing the full file."""
    with open(file_path, "rb") as f:
        header = f.read(4096)

    match = _NAMESPACE_RE.search(header)
    if match:
        return match.group(1).decode("utf-8")

    raise SaftParseError(
        "Could not detect SAF-T namespace. "
        "Ensure the file is a valid SAF-T PT XML."
    )


def detect_saft_type(tax_accounting_basis: str) -> SaftType:
    """Determine the SAF-T type from the TaxAccountingBasis header value."""
    return _BASIS_TO_TYPE.get(tax_accounting_basis, SaftType.INVOICING)


def get_xsd_filename(namespace: str) -> str | None:
    """Return the XSD filename for a given namespace, or None if unknown."""
    return NAMESPACE_XSD_MAP.get(namespace)
