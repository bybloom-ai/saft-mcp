"""Portuguese tax business rules validation."""

from __future__ import annotations

import re
from datetime import date

from saft_mcp.parser.models import Invoice, SaftData
from saft_mcp.validators.hash_chain import extract_number, extract_series
from saft_mcp.validators.nif import validate_nif

_ATCUD_RE = re.compile(r"^[A-Z0-9]{8}-\d+$")

VALID_INVOICE_TYPES = {"FT", "FS", "FR", "NC", "ND"}
VALID_INVOICE_STATUSES = {"N", "A", "F", "S"}
VALID_TAX_CODES = {"NOR", "INT", "RED", "ISE", "OUT", "NS", "NA"}


class ValidationResult:
    __slots__ = ("severity", "rule", "location", "message", "suggestion")

    def __init__(
        self,
        severity: str,
        rule: str,
        location: str,
        message: str,
        suggestion: str = "",
    ):
        self.severity = severity
        self.rule = rule
        self.location = location
        self.message = message
        self.suggestion = suggestion

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "rule": self.rule,
            "location": self.location,
            "message": self.message,
            "suggestion": self.suggestion,
        }


def validate_nifs(data: SaftData) -> list[ValidationResult]:
    """Validate all NIFs in the file."""
    results: list[ValidationResult] = []

    # Company NIF
    valid, info = validate_nif(data.metadata.tax_registration_number)
    if not valid:
        results.append(
            ValidationResult(
                "error", "nif", "Header/TaxRegistrationNumber",
                f"Company NIF {data.metadata.tax_registration_number} is invalid: {info}",
                "Check the company NIF in the invoicing software settings.",
            )
        )

    # Customer NIFs
    for cust in data.customers:
        valid, info = validate_nif(cust.customer_tax_id)
        if not valid:
            results.append(
                ValidationResult(
                    "warning", "nif",
                    f"Customer/{cust.customer_id}",
                    f"Customer {cust.company_name} has invalid NIF {cust.customer_tax_id}: {info}",
                )
            )

    return results


def validate_numbering(data: SaftData) -> list[ValidationResult]:
    """Check invoice numbering sequences for gaps."""
    results: list[ValidationResult] = []

    series_map: dict[str, list[Invoice]] = {}
    for inv in data.invoices:
        series = extract_series(inv.invoice_no)
        series_map.setdefault(series, []).append(inv)

    for series, invoices in series_map.items():
        sorted_invs = sorted(invoices, key=lambda i: extract_number(i.invoice_no))
        for i in range(1, len(sorted_invs)):
            prev_num = extract_number(sorted_invs[i - 1].invoice_no)
            curr_num = extract_number(sorted_invs[i].invoice_no)
            if curr_num != prev_num + 1:
                results.append(
                    ValidationResult(
                        "error", "numbering",
                        f"SalesInvoices/Invoice/{sorted_invs[i].invoice_no}",
                        f"Numbering gap in series {series}: "
                        f"{sorted_invs[i - 1].invoice_no} -> {sorted_invs[i].invoice_no}",
                        "Check if invoices were deleted or exported incorrectly.",
                    )
                )

    return results


def validate_atcud(data: SaftData) -> list[ValidationResult]:
    """Validate ATCUD presence and format on all documents."""
    results: list[ValidationResult] = []

    # Only enforce for files with dates >= 2023
    is_post_2023 = data.metadata.start_date >= date(2023, 1, 1)
    severity = "error" if is_post_2023 else "warning"

    for inv in data.invoices:
        if not inv.atcud:
            results.append(
                ValidationResult(
                    severity, "atcud",
                    f"SalesInvoices/Invoice/{inv.invoice_no}",
                    f"Missing ATCUD on {inv.invoice_no}",
                    "ATCUD is mandatory since January 2023.",
                )
            )
        elif not _ATCUD_RE.match(inv.atcud):
            results.append(
                ValidationResult(
                    "warning", "atcud",
                    f"SalesInvoices/Invoice/{inv.invoice_no}",
                    f"ATCUD format invalid on {inv.invoice_no}: {inv.atcud}",
                    "Expected format: XXXXXXXX-N (8 alphanumeric chars, dash, sequential number).",
                )
            )

    return results


def validate_tax_codes(data: SaftData) -> list[ValidationResult]:
    """Check that tax codes in invoice lines are valid."""
    results: list[ValidationResult] = []

    for inv in data.invoices:
        for line in inv.lines:
            if line.tax.tax_code not in VALID_TAX_CODES:
                results.append(
                    ValidationResult(
                        "warning", "tax_codes",
                        f"Invoice/{inv.invoice_no}/Line/{line.line_number}",
                        f"Unknown tax code '{line.tax.tax_code}' on line {line.line_number}",
                    )
                )
            # ISE lines must have exemption reason
            if line.tax.tax_code == "ISE" and not line.tax_exemption_reason:
                results.append(
                    ValidationResult(
                        "error", "tax_codes",
                        f"Invoice/{inv.invoice_no}/Line/{line.line_number}",
                        f"Tax-exempt line missing TaxExemptionReason on "
                        f"{inv.invoice_no} line {line.line_number}",
                        "ISE (exempt) lines must include a "
                        "TaxExemptionReason per Portuguese tax law.",
                    )
                )

    return results


def validate_control_totals(data: SaftData) -> list[ValidationResult]:
    """Verify section control totals match computed values."""
    results: list[ValidationResult] = []

    if data.sales_invoices_totals is not None:
        expected_count = data.sales_invoices_totals.number_of_entries
        actual_count = len(data.invoices)
        if expected_count != actual_count:
            results.append(
                ValidationResult(
                    "error", "control_totals",
                    "SalesInvoices/NumberOfEntries",
                    f"SalesInvoices declares {expected_count} entries "
                    f"but file contains {actual_count}",
                )
            )

    if data.payments_totals is not None:
        expected_count = data.payments_totals.number_of_entries
        actual_count = len(data.payments)
        if expected_count != actual_count:
            results.append(
                ValidationResult(
                    "error", "control_totals",
                    "Payments/NumberOfEntries",
                    f"Payments declares {expected_count} entries but file contains {actual_count}",
                )
            )

    return results


def run_all_business_rules(data: SaftData) -> list[ValidationResult]:
    """Run all business rule validations."""
    results: list[ValidationResult] = []
    results.extend(validate_nifs(data))
    results.extend(validate_numbering(data))
    results.extend(validate_atcud(data))
    results.extend(validate_tax_codes(data))
    results.extend(validate_control_totals(data))
    return results
