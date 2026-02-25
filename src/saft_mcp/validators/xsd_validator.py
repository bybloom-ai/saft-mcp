"""XSD schema validation for SAF-T PT files."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from lxml import etree

from saft_mcp.parser.detector import get_xsd_filename

_SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"
_XS_NS = "http://www.w3.org/2001/XMLSchema"


def _strip_xsd11_features(xsd_doc: etree._ElementTree) -> None:
    """Downgrade XSD 1.1 features to XSD 1.0 compatible equivalents.

    The official SAF-T PT v1.04_01 XSD uses XSD 1.1 features:
    - xs:assert for conditional field validation
    - xs:all with maxOccurs="unbounded" children

    lxml only supports XSD 1.0, so we:
    1. Remove xs:assert elements (business rules validator covers these)
    2. Convert xs:all to xs:sequence (real SAF-T files use consistent ordering)
    """
    ns = {"xs": _XS_NS}

    for assert_el in cast(list[etree._Element], xsd_doc.xpath("//xs:assert", namespaces=ns)):
        parent = assert_el.getparent()
        if parent is not None:
            parent.remove(assert_el)

    # xs:all with maxOccurs > 1 children is XSD 1.1 only.
    # Convert all xs:all to xs:sequence for compatibility.
    for all_el in cast(list[etree._Element], xsd_doc.xpath("//xs:all", namespaces=ns)):
        all_el.tag = f"{{{_XS_NS}}}sequence"


def validate_xsd(file_path: str, namespace: str) -> list[dict[str, str]]:
    """Validate a SAF-T file against its XSD schema.

    Returns a list of error dicts with 'severity', 'rule', 'location', 'message'.
    Returns empty list if valid or if XSD is not available for the namespace.
    """
    xsd_filename = get_xsd_filename(namespace)
    if xsd_filename is None:
        return [
            {
                "severity": "warning",
                "rule": "xsd",
                "location": "AuditFile",
                "message": f"No XSD schema available for namespace {namespace}",
                "suggestion": "XSD validation skipped. Business rules still apply.",
            }
        ]

    xsd_path = _SCHEMAS_DIR / xsd_filename
    if not xsd_path.exists():
        return [
            {
                "severity": "warning",
                "rule": "xsd",
                "location": "AuditFile",
                "message": f"XSD schema file not found: {xsd_filename}",
                "suggestion": f"Place {xsd_filename} in the schemas/ directory.",
            }
        ]

    try:
        xsd_doc = etree.parse(str(xsd_path))
        _strip_xsd11_features(xsd_doc)
        schema = etree.XMLSchema(xsd_doc)
    except etree.XMLSchemaParseError as e:
        return [
            {
                "severity": "error",
                "rule": "xsd",
                "location": "XSD",
                "message": f"Failed to parse XSD schema: {e}",
                "suggestion": "",
            }
        ]

    try:
        doc = etree.parse(file_path)
    except etree.XMLSyntaxError as e:
        return [
            {
                "severity": "error",
                "rule": "xsd",
                "location": "AuditFile",
                "message": f"XML syntax error: {e}",
                "suggestion": "",
            }
        ]

    is_valid = schema.validate(doc)
    if is_valid:
        return []

    results: list[dict[str, str]] = []
    for error in schema.error_log:  # type: ignore[attr-defined]
        results.append(
            {
                "severity": "error",
                "rule": "xsd",
                "location": f"Line {error.line}",
                "message": str(error.message),
                "suggestion": "",
            }
        )
        if len(results) >= 50:
            error_count = len(list(schema.error_log))  # type: ignore[call-overload]
            results.append(
                {
                    "severity": "info",
                    "rule": "xsd",
                    "location": "",
                    "message": f"Showing first 50 of {error_count} XSD errors",
                    "suggestion": "",
                }
            )
            break

    return results
