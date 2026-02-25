"""FastMCP server entry point -- registers all SAF-T tools."""

from __future__ import annotations

from mcp.server.fastmcp import Context, FastMCP

from saft_mcp.exceptions import SaftError
from saft_mcp.state import session_store
from saft_mcp.tools.get_invoice import get_invoice
from saft_mcp.tools.load import load_saft
from saft_mcp.tools.query_customers import query_customers
from saft_mcp.tools.query_invoices import query_invoices
from saft_mcp.tools.query_products import query_products
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


async def _get_session(ctx: Context):
    session_id = getattr(ctx, "session_id", "default")
    return await session_store.get(session_id)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def saft_load(ctx: Context, file_path: str) -> dict:
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
    ctx: Context,
    rules: list[str] | None = None,
) -> dict:
    """Validate the loaded SAF-T file against XSD and Portuguese business rules.

    Args:
        rules: Specific rules to check (xsd, numbering, hash_chain, control_totals,
               nif, tax_codes, atcud). Defaults to all.

    Returns validation results with severity, location, and suggestions.
    """
    session = await _get_session(ctx)
    return validate_saft(session, rules)


@mcp.tool()
async def saft_summary(ctx: Context) -> dict:
    """Generate an executive summary of the loaded SAF-T file.

    Returns revenue totals, invoice counts, VAT breakdown, top customers,
    and document type distribution.
    """
    session = await _get_session(ctx)
    return summarize_saft(session)


@mcp.tool()
async def saft_query_invoices(
    ctx: Context,
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
) -> dict:
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
    ctx: Context,
    date_from: str | None = None,
    date_to: str | None = None,
    group_by: str = "rate",
) -> dict:
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
    ctx: Context,
    name: str | None = None,
    nif: str | None = None,
    city: str | None = None,
    country: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict:
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
    ctx: Context,
    description: str | None = None,
    code: str | None = None,
    product_type: str | None = None,
    group: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict:
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
async def saft_get_invoice(ctx: Context, invoice_no: str) -> dict:
    """Get full detail for a single invoice including all line items.

    Args:
        invoice_no: Exact invoice number (e.g. "FR 2025A15/90").

    Returns complete invoice with header, document totals, special regimes,
    and all line items with product, quantity, price, tax, and references.
    """
    session = await _get_session(ctx)
    return get_invoice(session, invoice_no=invoice_no)
