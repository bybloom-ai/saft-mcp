"""FastMCP server entry point -- registers all SAF-T tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from saft_mcp.exceptions import SaftError
from saft_mcp.state import SessionState, session_store
from saft_mcp.tools.aging import aging_analysis
from saft_mcp.tools.anomaly_detect import detect_anomalies
from saft_mcp.tools.compare import compare_saft
from saft_mcp.tools.export import export_csv
from saft_mcp.tools.get_invoice import get_invoice
from saft_mcp.tools.load import load_saft
from saft_mcp.tools.query_customers import query_customers
from saft_mcp.tools.query_invoices import query_invoices
from saft_mcp.tools.query_products import query_products
from saft_mcp.tools.stats import compute_stats
from saft_mcp.tools.summary import summarize_saft
from saft_mcp.tools.tax_summary import tax_summary
from saft_mcp.tools.validate import validate_saft

mcp = FastMCP(
    "saft-mcp",
    instructions=(
        "SAF-T MCP Server -- Parse and analyze Portuguese SAF-T XML files. "
        "Start by calling saft_load with a file path, then use other tools "
        "to validate, summarize, and query the data."
    ),
)


async def _get_session(ctx: Context[Any, Any]) -> SessionState:
    session_id = getattr(ctx, "session_id", "default")
    return await session_store.get(session_id)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def saft_load(ctx: Context[Any, Any], file_path: str) -> dict[str, Any]:
    """Load and parse a SAF-T PT XML file.

    Args:
        file_path: Path to the SAF-T XML file.

    Returns file metadata: company name, NIF, fiscal period, record counts.
    """
    try:
        session = await _get_session(ctx)
        return load_saft(session, file_path)
    except SaftError as e:
        return {"error": str(e), "suggestion": "Check the file path and try again."}


@mcp.tool()
async def saft_validate(
    ctx: Context[Any, Any],
    rules: list[str] | None = None,
) -> dict[str, Any]:
    """Validate the loaded SAF-T file against XSD and Portuguese business rules.

    Args:
        rules: Specific rules to check (xsd, numbering, hash_chain, control_totals,
               nif, tax_codes, atcud). Defaults to all.

    Returns validation results with severity, location, and suggestions.
    """
    session = await _get_session(ctx)
    return validate_saft(session, rules)


@mcp.tool()
async def saft_summary(ctx: Context[Any, Any]) -> dict[str, Any]:
    """Generate an executive summary of the loaded SAF-T file.

    Returns revenue totals, invoice counts, VAT breakdown, top customers,
    and document type distribution.
    """
    session = await _get_session(ctx)
    return summarize_saft(session)


@mcp.tool()
async def saft_query_invoices(
    ctx: Context[Any, Any],
    date_from: str | None = None,
    date_to: str | None = None,
    customer_nif: str | None = None,
    customer_name: str | None = None,
    doc_type: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """Search and filter invoices in the loaded SAF-T file.

    Args:
        date_from: Start date filter (ISO format YYYY-MM-DD).
        date_to: End date filter (ISO format YYYY-MM-DD).
        customer_nif: Filter by customer tax ID (partial match).
        customer_name: Filter by customer name (case-insensitive partial match).
        doc_type: Document type: FT (invoice), FR (invoice-receipt), NC (credit note),
                  ND (debit note), FS (simplified invoice).
        min_amount: Minimum gross total.
        max_amount: Maximum gross total.
        status: Invoice status: N (normal), A (cancelled), F (invoiced).
        limit: Max results per page (default 50, max 500).
        offset: Pagination offset.

    Returns paginated list of invoices.
    """
    session = await _get_session(ctx)
    return query_invoices(
        session,
        date_from=date_from,
        date_to=date_to,
        customer_nif=customer_nif,
        customer_name=customer_name,
        doc_type=doc_type,
        min_amount=min_amount,
        max_amount=max_amount,
        status=status,
        limit=limit,
        offset=offset,
    )


@mcp.tool()
async def saft_tax_summary(
    ctx: Context[Any, Any],
    date_from: str | None = None,
    date_to: str | None = None,
    group_by: str = "rate",
) -> dict[str, Any]:
    """Generate a VAT analysis of the loaded SAF-T file.

    Args:
        date_from: Start date filter (ISO format YYYY-MM-DD).
        date_to: End date filter (ISO format YYYY-MM-DD).
        group_by: Group results by "rate" (default), "month", or "doc_type".

    Returns VAT totals per group: taxable base, tax amount, gross total.
    """
    session = await _get_session(ctx)
    return tax_summary(session, date_from=date_from, date_to=date_to, group_by=group_by)


@mcp.tool()
async def saft_query_customers(
    ctx: Context[Any, Any],
    name: str | None = None,
    nif: str | None = None,
    city: str | None = None,
    country: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """Search and filter customers in the loaded SAF-T file.

    Args:
        name: Filter by company name (case-insensitive partial match).
        nif: Filter by customer tax ID (partial match).
        city: Filter by billing address city (case-insensitive partial match).
        country: Filter by country code (exact match, e.g. "PT", "ES").
        limit: Max results per page (default 50, max 500).
        offset: Pagination offset.

    Returns paginated list of customers with revenue stats.
    """
    session = await _get_session(ctx)
    return query_customers(
        session,
        name=name,
        nif=nif,
        city=city,
        country=country,
        limit=limit,
        offset=offset,
    )


@mcp.tool()
async def saft_query_products(
    ctx: Context[Any, Any],
    description: str | None = None,
    code: str | None = None,
    product_type: str | None = None,
    group: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """Search and filter products in the loaded SAF-T file.

    Args:
        description: Filter by product description (case-insensitive partial match).
        code: Filter by product code (partial match).
        product_type: Filter by type: P (product), S (service), O (other),
                      I (import), E (export).
        group: Filter by product group (case-insensitive partial match).
        limit: Max results per page (default 50, max 500).
        offset: Pagination offset.

    Returns paginated list of products with sales stats.
    """
    session = await _get_session(ctx)
    return query_products(
        session,
        description=description,
        code=code,
        product_type=product_type,
        group=group,
        limit=limit,
        offset=offset,
    )


@mcp.tool()
async def saft_get_invoice(ctx: Context[Any, Any], invoice_no: str) -> dict[str, Any]:
    """Get full detail for a single invoice including all line items.

    Args:
        invoice_no: Exact invoice number (e.g. "FR 2025A15/90").

    Returns complete invoice with header, document totals, special regimes,
    and all line items with product, quantity, price, tax, and references.
    """
    session = await _get_session(ctx)
    return get_invoice(session, invoice_no=invoice_no)


@mcp.tool()
async def saft_anomaly_detect(
    ctx: Context[Any, Any],
    checks: list[str] | None = None,
) -> dict[str, Any]:
    """Detect suspicious patterns in the loaded SAF-T file.

    Args:
        checks: Specific checks to run. Defaults to all. Available checks:
                duplicate_invoices, numbering_gaps, weekend_invoices,
                unusual_amounts, cancelled_ratio, zero_amount.

    Returns list of anomalies with type, severity, description, and affected documents.
    """
    session = await _get_session(ctx)
    return detect_anomalies(session, checks=checks)


@mcp.tool()
async def saft_compare(
    ctx: Context[Any, Any],
    file_path: str,
    metrics: list[str] | None = None,
) -> dict[str, Any]:
    """Compare the loaded SAF-T file against a second file.

    Args:
        file_path: Path to the second SAF-T XML file to compare against.
        metrics: Specific metrics to compare. Defaults to all. Available:
                 revenue, customers, products, doc_types, vat.

    Returns period labels and a changes dict with before/after/delta per metric.
    """
    session = await _get_session(ctx)
    return compare_saft(session, file_path=file_path, metrics=metrics)


@mcp.tool()
async def saft_aging(
    ctx: Context[Any, Any],
    reference_date: str | None = None,
    buckets: list[int] | None = None,
) -> dict[str, Any]:
    """Compute accounts receivable aging from invoices and payments.

    Args:
        reference_date: Date to age from (ISO format YYYY-MM-DD). Defaults to today.
        buckets: Aging bucket boundaries in days. Defaults to [30, 60, 90, 120].

    Returns per-customer aging with amounts in each bucket, sorted by outstanding amount.
    """
    session = await _get_session(ctx)
    return aging_analysis(session, reference_date=reference_date, buckets=buckets)


@mcp.tool()
async def saft_export(
    ctx: Context[Any, Any],
    export_type: str,
    file_path: str,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Export query results to a CSV file.

    Args:
        export_type: What to export: invoices, customers, products, tax_summary, anomalies.
        file_path: Output CSV file path.
        filters: Optional filters (same as the corresponding query tool parameters).

    Returns file path, row count, and column names.
    """
    session = await _get_session(ctx)
    return export_csv(session, export_type=export_type, file_path=file_path, filters=filters)


@mcp.tool()
async def saft_stats(
    ctx: Context[Any, Any],
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """Generate statistical overview of the loaded SAF-T file.

    Args:
        date_from: Start date filter (ISO format YYYY-MM-DD).
        date_to: End date filter (ISO format YYYY-MM-DD).

    Returns invoice statistics (mean, median, std deviation), daily/weekly/monthly
    distributions, customer concentration (Pareto), and top/bottom invoices.
    """
    session = await _get_session(ctx)
    return compute_stats(session, date_from=date_from, date_to=date_to)
