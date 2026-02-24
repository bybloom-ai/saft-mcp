"""saft_validate tool -- Validate a loaded SAF-T file."""

from __future__ import annotations

from saft_mcp.parser.detector import detect_namespace
from saft_mcp.state import SessionState
from saft_mcp.validators.business_rules import (
    run_all_business_rules,
)
from saft_mcp.validators.hash_chain import verify_hash_chain
from saft_mcp.validators.xsd_validator import validate_xsd

ALL_RULES = {"xsd", "numbering", "hash_chain", "control_totals", "nif", "tax_codes", "atcud"}


def validate_saft(
    session: SessionState,
    rules: list[str] | None = None,
) -> dict:
    """Validate the loaded SAF-T file.

    Args:
        session: Current session with loaded file.
        rules: Specific rules to check. Defaults to all.

    Returns:
        ValidateResponse-style dict.
    """
    if session.loaded_file is None or session.file_path is None:
        return {
            "error": "No SAF-T file loaded. Use saft_load first.",
            "suggestion": "Call saft_load with the path to your SAF-T XML file.",
        }

    requested_rules = set(rules) if rules else ALL_RULES
    all_results: list[dict] = []

    # XSD validation (runs against the file on disk)
    if "xsd" in requested_rules:
        ns = detect_namespace(session.file_path)
        xsd_results = validate_xsd(session.file_path, ns)
        all_results.extend(xsd_results)

    # Business rules (runs against the parsed data)
    business_rule_names = requested_rules - {"xsd", "hash_chain"}
    if business_rule_names:
        br_results = run_all_business_rules(session.loaded_file)
        for r in br_results:
            if r.rule in requested_rules:
                all_results.append(r.to_dict())

    # Hash chain verification
    if "hash_chain" in requested_rules and session.loaded_file.invoices:
        chain_results = verify_hash_chain(session.loaded_file.invoices)
        for cr in chain_results:
            if not cr.chain_intact:
                for issue in cr.issues:
                    all_results.append({
                        "severity": "error",
                        "rule": "hash_chain",
                        "location": f"Series {cr.series}",
                        "message": issue,
                        "suggestion": "",
                    })

    error_count = sum(1 for r in all_results if r["severity"] == "error")
    warning_count = sum(1 for r in all_results if r["severity"] == "warning")

    return {
        "valid": error_count == 0,
        "error_count": error_count,
        "warning_count": warning_count,
        "results": all_results,
    }
