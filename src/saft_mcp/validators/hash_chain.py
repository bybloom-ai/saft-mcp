"""Invoice hash chain verification."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field

from saft_mcp.parser.models import Invoice

_INVOICE_NO_RE = re.compile(r"^(?P<series>.+)/(?P<number>\d+)$")


def extract_series(invoice_no: str) -> str:
    """Extract the series prefix from an invoice number."""
    m = _INVOICE_NO_RE.match(invoice_no.strip())
    if m:
        return m.group("series").strip()
    stripped = invoice_no.rstrip("0123456789").rstrip("/").strip()
    return stripped or invoice_no


def extract_number(invoice_no: str) -> int:
    """Extract the sequential number from an invoice number."""
    m = _INVOICE_NO_RE.match(invoice_no.strip())
    if m:
        return int(m.group("number"))
    trailing = re.search(r"(\d+)$", invoice_no)
    if trailing:
        return int(trailing.group(1))
    return 0


@dataclass
class HashChainResult:
    series: str
    total_invoices: int
    chain_intact: bool
    issues: list[str] = field(default_factory=list)


def verify_hash_chain(invoices: list[Invoice]) -> list[HashChainResult]:
    """Verify hash chain integrity for each invoice series.

    Groups invoices by series, checks sequential ordering and hash format.
    """
    series_map: dict[str, list[Invoice]] = {}
    for inv in invoices:
        series = extract_series(inv.invoice_no)
        series_map.setdefault(series, []).append(inv)

    results = []
    for series, series_invoices in series_map.items():
        sorted_invs = sorted(series_invoices, key=lambda i: extract_number(i.invoice_no))
        issues: list[str] = []

        for i, inv in enumerate(sorted_invs):
            # Check hash presence
            if not inv.hash or inv.hash == "0":
                issues.append(f"{inv.invoice_no}: missing hash")
                continue

            # Check hash format (Base64-encoded RSA-SHA1 = 172 chars -> 128 bytes)
            try:
                decoded = base64.b64decode(inv.hash)
                if len(decoded) != 128:
                    issues.append(
                        f"{inv.invoice_no}: hash length {len(decoded)} bytes, expected 128"
                    )
            except Exception:
                issues.append(f"{inv.invoice_no}: invalid Base64 hash")

            # Check sequential numbering
            if i > 0:
                prev_num = extract_number(sorted_invs[i - 1].invoice_no)
                curr_num = extract_number(inv.invoice_no)
                if curr_num != prev_num + 1:
                    issues.append(
                        f"Numbering gap: {sorted_invs[i - 1].invoice_no} -> {inv.invoice_no}"
                    )

        results.append(
            HashChainResult(
                series=series,
                total_invoices=len(series_invoices),
                chain_intact=len(issues) == 0,
                issues=issues,
            )
        )

    return results
