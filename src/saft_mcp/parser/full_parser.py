"""Full DOM parser for SAF-T PT XML files (< 50 MB).

Parses the entire XML into memory as a SaftData Pydantic model.
Tolerates vendor quirks (empty elements, encoding issues, etc.).
"""

from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from lxml import etree

from saft_mcp.exceptions import SaftParseError
from saft_mcp.parser.detector import detect_namespace, detect_saft_type
from saft_mcp.parser.models import (
    Address,
    CurrencyAmount,
    Customer,
    DocumentStatus,
    DocumentTotals,
    FileMetadata,
    Invoice,
    InvoiceLine,
    LineReference,
    LineTax,
    MovementDocument,
    MovementLine,
    MovementStatus,
    Payment,
    PaymentLine,
    PaymentStatus,
    Product,
    SaftData,
    SectionTotals,
    SourceDocumentID,
    SpecialRegimes,
    Supplier,
    TaxEntry,
    WorkingDocument,
    WorkingDocumentLine,
    WorkingDocumentStatus,
)

# ---------------------------------------------------------------------------
# XML helper functions (vendor-quirk tolerant)
# ---------------------------------------------------------------------------


def _t(element: etree._Element | None, tag: str, ns: str, default: str = "") -> str:
    """Extract text from a child element, tolerating missing/empty tags."""
    if element is None:
        return default
    child = element.find(f"{{{ns}}}{tag}")
    if child is None or child.text is None:
        return default
    return child.text.strip()


def _d(element: etree._Element | None, tag: str, ns: str) -> Decimal:
    """Extract a Decimal value, defaulting to zero."""
    text = _t(element, tag, ns, "0")
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal("0")


def _int(element: etree._Element | None, tag: str, ns: str, default: int = 0) -> int:
    """Extract an integer value."""
    text = _t(element, tag, ns, str(default))
    try:
        return int(text)
    except ValueError:
        return default


def _date(element: etree._Element | None, tag: str, ns: str) -> date | None:
    """Extract a date with tolerance for non-standard formats."""
    text = _t(element, tag, ns)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    # Flexible fallback for non-zero-padded dates
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _datetime(element: etree._Element | None, tag: str, ns: str) -> datetime | None:
    """Extract a datetime value."""
    text = _t(element, tag, ns)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _find(element: etree._Element, tag: str, ns: str) -> etree._Element | None:
    """Find a child element by tag."""
    return element.find(f"{{{ns}}}{tag}")


def _findall(element: etree._Element, tag: str, ns: str) -> list[etree._Element]:
    """Find all child elements by tag."""
    return element.findall(f"{{{ns}}}{tag}")


# ---------------------------------------------------------------------------
# Section parsers
# ---------------------------------------------------------------------------


def _parse_address(elem: etree._Element | None, ns: str) -> Address:
    """Parse an Address or CompanyAddress element."""
    if elem is None:
        return Address()
    # Address may be nested inside a wrapper (e.g. <ShipFrom><Address>)
    addr = _find(elem, "Address", ns)
    if addr is not None:
        elem = addr
    return Address(
        address_detail=_t(elem, "AddressDetail", ns),
        city=_t(elem, "City", ns),
        postal_code=_t(elem, "PostalCode", ns),
        region=_t(elem, "Region", ns),
        country=_t(elem, "Country", ns, "PT"),
    )


def _parse_header(root: etree._Element, ns: str, file_path: str) -> FileMetadata:
    """Parse the Header section."""
    header = _find(root, "Header", ns)
    if header is None:
        raise SaftParseError("Missing <Header> element in SAF-T file.")

    tax_basis = _t(header, "TaxAccountingBasis", ns, "F")
    saft_type = detect_saft_type(tax_basis)

    return FileMetadata(
        audit_file_version=_t(header, "AuditFileVersion", ns),
        company_id=_t(header, "CompanyID", ns),
        tax_registration_number=_t(header, "TaxRegistrationNumber", ns),
        tax_accounting_basis=tax_basis,
        company_name=_t(header, "CompanyName", ns),
        business_name=_t(header, "BusinessName", ns),
        company_address=_parse_address(_find(header, "CompanyAddress", ns), ns),
        fiscal_year=_int(header, "FiscalYear", ns),
        start_date=_date(header, "StartDate", ns) or date(2000, 1, 1),
        end_date=_date(header, "EndDate", ns) or date(2000, 12, 31),
        currency_code=_t(header, "CurrencyCode", ns, "EUR"),
        date_created=_date(header, "DateCreated", ns),
        tax_entity=_t(header, "TaxEntity", ns),
        product_company_tax_id=_t(header, "ProductCompanyTaxID", ns),
        software_certificate_number=_t(header, "SoftwareCertificateNumber", ns),
        product_id=_t(header, "ProductID", ns),
        product_version=_t(header, "ProductVersion", ns),
        telephone=_t(header, "Telephone", ns),
        email=_t(header, "Email", ns),
        website=_t(header, "Website", ns),
        saft_type=saft_type,
        file_size_bytes=os.path.getsize(file_path),
    )


def _parse_customers(master_files: etree._Element | None, ns: str) -> list[Customer]:
    if master_files is None:
        return []
    customers = []
    for elem in _findall(master_files, "Customer", ns):
        customers.append(
            Customer(
                customer_id=_t(elem, "CustomerID", ns),
                account_id=_t(elem, "AccountID", ns),
                customer_tax_id=_t(elem, "CustomerTaxID", ns),
                company_name=_t(elem, "CompanyName", ns),
                billing_address=_parse_address(_find(elem, "BillingAddress", ns), ns),
                self_billing_indicator=_int(elem, "SelfBillingIndicator", ns),
            )
        )
    return customers


def _parse_suppliers(master_files: etree._Element | None, ns: str) -> list[Supplier]:
    if master_files is None:
        return []
    suppliers = []
    for elem in _findall(master_files, "Supplier", ns):
        suppliers.append(
            Supplier(
                supplier_id=_t(elem, "SupplierID", ns),
                account_id=_t(elem, "AccountID", ns),
                supplier_tax_id=_t(elem, "SupplierTaxID", ns),
                company_name=_t(elem, "CompanyName", ns),
                billing_address=_parse_address(_find(elem, "BillingAddress", ns), ns),
                self_billing_indicator=_int(elem, "SelfBillingIndicator", ns),
            )
        )
    return suppliers


def _parse_products(master_files: etree._Element | None, ns: str) -> list[Product]:
    if master_files is None:
        return []
    products = []
    for elem in _findall(master_files, "Product", ns):
        products.append(
            Product(
                product_type=_t(elem, "ProductType", ns),
                product_code=_t(elem, "ProductCode", ns),
                product_group=_t(elem, "ProductGroup", ns),
                product_description=_t(elem, "ProductDescription", ns),
                product_number_code=_t(elem, "ProductNumberCode", ns),
            )
        )
    return products


def _parse_tax_table(master_files: etree._Element | None, ns: str) -> list[TaxEntry]:
    if master_files is None:
        return []
    table = _find(master_files, "TaxTable", ns)
    if table is None:
        return []
    entries = []
    for elem in _findall(table, "TaxTableEntry", ns):
        entries.append(
            TaxEntry(
                tax_type=_t(elem, "TaxType", ns),
                tax_country_region=_t(elem, "TaxCountryRegion", ns),
                tax_code=_t(elem, "TaxCode", ns),
                description=_t(elem, "Description", ns),
                tax_percentage=_d(elem, "TaxPercentage", ns),
            )
        )
    return entries


def _parse_line_tax(elem: etree._Element, ns: str) -> LineTax:
    tax_elem = _find(elem, "Tax", ns)
    if tax_elem is None:
        return LineTax(
            tax_type="IVA",
            tax_country_region="PT",
            tax_code="NOR",
            tax_percentage=Decimal("0"),
        )
    return LineTax(
        tax_type=_t(tax_elem, "TaxType", ns, "IVA"),
        tax_country_region=_t(tax_elem, "TaxCountryRegion", ns, "PT"),
        tax_code=_t(tax_elem, "TaxCode", ns),
        tax_percentage=_d(tax_elem, "TaxPercentage", ns),
    )


def _parse_document_totals(elem: etree._Element, ns: str) -> DocumentTotals:
    dt = _find(elem, "DocumentTotals", ns)
    if dt is None:
        return DocumentTotals(
            tax_payable=Decimal("0"),
            net_total=Decimal("0"),
            gross_total=Decimal("0"),
        )
    currency = None
    curr_elem = _find(dt, "Currency", ns)
    if curr_elem is not None:
        currency = CurrencyAmount(
            currency_code=_t(curr_elem, "CurrencyCode", ns),
            currency_amount=_d(curr_elem, "CurrencyAmount", ns),
            exchange_rate=_d(curr_elem, "ExchangeRate", ns),
        )
    return DocumentTotals(
        tax_payable=_d(dt, "TaxPayable", ns),
        net_total=_d(dt, "NetTotal", ns),
        gross_total=_d(dt, "GrossTotal", ns),
        currency=currency,
    )


def _parse_section_totals(section: etree._Element | None, ns: str) -> SectionTotals | None:
    if section is None:
        return None
    noe = _t(section, "NumberOfEntries", ns)
    if not noe:
        return None
    return SectionTotals(
        number_of_entries=int(noe),
        total_debit=_d(section, "TotalDebit", ns),
        total_credit=_d(section, "TotalCredit", ns),
    )


# -- SalesInvoices --


def _parse_invoice_line(elem: etree._Element, ns: str) -> InvoiceLine:
    refs_elem = _find(elem, "References", ns)
    refs = None
    if refs_elem is not None:
        refs = LineReference(
            reference=_t(refs_elem, "Reference", ns),
            reason=_t(refs_elem, "Reason", ns),
        )
    return InvoiceLine(
        line_number=_int(elem, "LineNumber", ns),
        product_code=_t(elem, "ProductCode", ns),
        product_description=_t(elem, "ProductDescription", ns),
        quantity=_d(elem, "Quantity", ns),
        unit_of_measure=_t(elem, "UnitOfMeasure", ns),
        unit_price=_d(elem, "UnitPrice", ns),
        tax_point_date=_date(elem, "TaxPointDate", ns),
        references=refs,
        description=_t(elem, "Description", ns),
        credit_amount=_d(elem, "CreditAmount", ns),
        debit_amount=_d(elem, "DebitAmount", ns),
        tax=_parse_line_tax(elem, ns),
        tax_exemption_reason=_t(elem, "TaxExemptionReason", ns),
        tax_exemption_code=_t(elem, "TaxExemptionCode", ns),
        settlement_amount=_d(elem, "SettlementAmount", ns),
    )


def _parse_invoice(elem: etree._Element, ns: str) -> Invoice:
    status_elem = _find(elem, "DocumentStatus", ns)
    status = DocumentStatus(
        invoice_status=_t(status_elem, "InvoiceStatus", ns),
        invoice_status_date=_datetime(status_elem, "InvoiceStatusDate", ns) or datetime(2000, 1, 1),
        reason=_t(status_elem, "Reason", ns),
        source_id=_t(status_elem, "SourceID", ns),
        source_billing=_t(status_elem, "SourceBilling", ns),
    )

    sr_elem = _find(elem, "SpecialRegimes", ns)
    special_regimes = SpecialRegimes(
        self_billing_indicator=_int(sr_elem, "SelfBillingIndicator", ns),
        cash_vat_scheme_indicator=_int(sr_elem, "CashVATSchemeIndicator", ns),
        third_parties_billing_indicator=_int(sr_elem, "ThirdPartiesBillingIndicator", ns),
    )

    lines = [_parse_invoice_line(le, ns) for le in _findall(elem, "Line", ns)]

    return Invoice(
        invoice_no=_t(elem, "InvoiceNo", ns),
        atcud=_t(elem, "ATCUD", ns),
        document_status=status,
        hash=_t(elem, "Hash", ns),
        hash_control=_t(elem, "HashControl", ns),
        invoice_date=_date(elem, "InvoiceDate", ns) or date(2000, 1, 1),
        invoice_type=_t(elem, "InvoiceType", ns),
        special_regimes=special_regimes,
        source_id=_t(elem, "SourceID", ns),
        eac_code=_t(elem, "EACCode", ns),
        system_entry_date=_datetime(elem, "SystemEntryDate", ns) or datetime(2000, 1, 1),
        customer_id=_t(elem, "CustomerID", ns),
        ship_to=_parse_address(_find(elem, "ShipTo", ns), ns)
        if _find(elem, "ShipTo", ns) is not None
        else None,
        ship_from=_parse_address(_find(elem, "ShipFrom", ns), ns)
        if _find(elem, "ShipFrom", ns) is not None
        else None,
        lines=lines,
        document_totals=_parse_document_totals(elem, ns),
    )


def _parse_invoices(
    source_docs: etree._Element | None, ns: str
) -> tuple[list[Invoice], SectionTotals | None]:
    if source_docs is None:
        return [], None
    sales = _find(source_docs, "SalesInvoices", ns)
    if sales is None:
        return [], None
    totals = _parse_section_totals(sales, ns)
    invoices = [_parse_invoice(e, ns) for e in _findall(sales, "Invoice", ns)]
    return invoices, totals


# -- Payments --


def _parse_payment_line(elem: etree._Element, ns: str) -> PaymentLine:
    sdid_elem = _find(elem, "SourceDocumentID", ns)
    sdid = None
    if sdid_elem is not None:
        sdid = SourceDocumentID(
            originating_on=_t(sdid_elem, "OriginatingON", ns),
            invoice_date=_date(sdid_elem, "InvoiceDate", ns) or date(2000, 1, 1),
        )

    tax_elem = _find(elem, "Tax", ns)
    tax = None
    if tax_elem is not None:
        tax = LineTax(
            tax_type=_t(tax_elem, "TaxType", ns, "IVA"),
            tax_country_region=_t(tax_elem, "TaxCountryRegion", ns, "PT"),
            tax_code=_t(tax_elem, "TaxCode", ns),
            tax_percentage=_d(tax_elem, "TaxPercentage", ns),
        )

    return PaymentLine(
        line_number=_int(elem, "LineNumber", ns),
        source_document_id=sdid,
        credit_amount=_d(elem, "CreditAmount", ns),
        debit_amount=_d(elem, "DebitAmount", ns),
        tax=tax,
    )


def _parse_payment(elem: etree._Element, ns: str) -> Payment:
    status_elem = _find(elem, "DocumentStatus", ns)
    status = PaymentStatus(
        payment_status=_t(status_elem, "PaymentStatus", ns),
        payment_status_date=_datetime(status_elem, "PaymentStatusDate", ns) or datetime(2000, 1, 1),
        reason=_t(status_elem, "Reason", ns),
        source_id=_t(status_elem, "SourceID", ns),
        source_payment=_t(status_elem, "SourcePayment", ns),
    )

    lines = [_parse_payment_line(le, ns) for le in _findall(elem, "Line", ns)]

    return Payment(
        payment_ref_no=_t(elem, "PaymentRefNo", ns),
        atcud=_t(elem, "ATCUD", ns),
        transaction_date=_date(elem, "TransactionDate", ns) or date(2000, 1, 1),
        payment_type=_t(elem, "PaymentType", ns),
        system_id=_t(elem, "SystemID", ns),
        document_status=status,
        source_id=_t(elem, "SourceID", ns),
        system_entry_date=_datetime(elem, "SystemEntryDate", ns) or datetime(2000, 1, 1),
        customer_id=_t(elem, "CustomerID", ns),
        lines=lines,
        document_totals=_parse_document_totals(elem, ns),
    )


def _parse_payments(
    source_docs: etree._Element | None, ns: str
) -> tuple[list[Payment], SectionTotals | None]:
    if source_docs is None:
        return [], None
    payments_section = _find(source_docs, "Payments", ns)
    if payments_section is None:
        return [], None
    totals = _parse_section_totals(payments_section, ns)
    payments = [_parse_payment(e, ns) for e in _findall(payments_section, "Payment", ns)]
    return payments, totals


# -- MovementOfGoods --


def _parse_movement_line(elem: etree._Element, ns: str) -> MovementLine:
    tax_elem = _find(elem, "Tax", ns)
    tax = None
    if tax_elem is not None:
        tax = LineTax(
            tax_type=_t(tax_elem, "TaxType", ns, "IVA"),
            tax_country_region=_t(tax_elem, "TaxCountryRegion", ns, "PT"),
            tax_code=_t(tax_elem, "TaxCode", ns),
            tax_percentage=_d(tax_elem, "TaxPercentage", ns),
        )
    return MovementLine(
        line_number=_int(elem, "LineNumber", ns),
        product_code=_t(elem, "ProductCode", ns),
        product_description=_t(elem, "ProductDescription", ns),
        quantity=_d(elem, "Quantity", ns),
        unit_of_measure=_t(elem, "UnitOfMeasure", ns),
        unit_price=_d(elem, "UnitPrice", ns),
        description=_t(elem, "Description", ns),
        credit_amount=_d(elem, "CreditAmount", ns),
        debit_amount=_d(elem, "DebitAmount", ns),
        tax=tax,
    )


def _parse_movement(elem: etree._Element, ns: str) -> MovementDocument:
    status_elem = _find(elem, "DocumentStatus", ns)
    status = MovementStatus(
        movement_status=_t(status_elem, "MovementStatus", ns),
        movement_status_date=_datetime(status_elem, "MovementStatusDate", ns)
        or datetime(2000, 1, 1),
        reason=_t(status_elem, "Reason", ns),
        source_id=_t(status_elem, "SourceID", ns),
        source_billing=_t(status_elem, "SourceBilling", ns),
    )

    lines = [_parse_movement_line(le, ns) for le in _findall(elem, "Line", ns)]

    return MovementDocument(
        document_number=_t(elem, "DocumentNumber", ns),
        atcud=_t(elem, "ATCUD", ns),
        document_status=status,
        hash=_t(elem, "Hash", ns),
        hash_control=_t(elem, "HashControl", ns),
        movement_date=_date(elem, "MovementDate", ns) or date(2000, 1, 1),
        movement_type=_t(elem, "MovementType", ns),
        system_entry_date=_datetime(elem, "SystemEntryDate", ns) or datetime(2000, 1, 1),
        source_id=_t(elem, "SourceID", ns),
        eac_code=_t(elem, "EACCode", ns),
        customer_id=_t(elem, "CustomerID", ns),
        ship_to=_parse_address(_find(elem, "ShipTo", ns), ns)
        if _find(elem, "ShipTo", ns) is not None
        else None,
        ship_from=_parse_address(_find(elem, "ShipFrom", ns), ns)
        if _find(elem, "ShipFrom", ns) is not None
        else None,
        movement_start_time=_datetime(elem, "MovementStartTime", ns),
        lines=lines,
        document_totals=_parse_document_totals(elem, ns),
    )


def _parse_movements(
    source_docs: etree._Element | None, ns: str
) -> tuple[list[MovementDocument], SectionTotals | None]:
    if source_docs is None:
        return [], None
    mog = _find(source_docs, "MovementOfGoods", ns)
    if mog is None:
        return [], None
    totals = _parse_section_totals(mog, ns)
    movements = [_parse_movement(e, ns) for e in _findall(mog, "StockMovement", ns)]
    return movements, totals


# -- WorkingDocuments --


def _parse_working_doc_line(elem: etree._Element, ns: str) -> WorkingDocumentLine:
    tax_elem = _find(elem, "Tax", ns)
    tax = None
    if tax_elem is not None:
        tax = LineTax(
            tax_type=_t(tax_elem, "TaxType", ns, "IVA"),
            tax_country_region=_t(tax_elem, "TaxCountryRegion", ns, "PT"),
            tax_code=_t(tax_elem, "TaxCode", ns),
            tax_percentage=_d(tax_elem, "TaxPercentage", ns),
        )
    return WorkingDocumentLine(
        line_number=_int(elem, "LineNumber", ns),
        product_code=_t(elem, "ProductCode", ns),
        product_description=_t(elem, "ProductDescription", ns),
        quantity=_d(elem, "Quantity", ns),
        unit_of_measure=_t(elem, "UnitOfMeasure", ns),
        unit_price=_d(elem, "UnitPrice", ns),
        description=_t(elem, "Description", ns),
        credit_amount=_d(elem, "CreditAmount", ns),
        debit_amount=_d(elem, "DebitAmount", ns),
        tax=tax,
    )


def _parse_working_doc(elem: etree._Element, ns: str) -> WorkingDocument:
    status_elem = _find(elem, "DocumentStatus", ns)
    status = WorkingDocumentStatus(
        document_status=_t(status_elem, "DocumentStatus", ns),
        document_status_date=_datetime(status_elem, "DocumentStatusDate", ns)
        or datetime(2000, 1, 1),
        reason=_t(status_elem, "Reason", ns),
        source_id=_t(status_elem, "SourceID", ns),
        source_billing=_t(status_elem, "SourceBilling", ns),
    )
    lines = [_parse_working_doc_line(le, ns) for le in _findall(elem, "Line", ns)]

    return WorkingDocument(
        document_number=_t(elem, "DocumentNumber", ns),
        atcud=_t(elem, "ATCUD", ns),
        document_status=status,
        hash=_t(elem, "Hash", ns),
        hash_control=_t(elem, "HashControl", ns),
        work_date=_date(elem, "WorkDate", ns) or date(2000, 1, 1),
        work_type=_t(elem, "WorkType", ns),
        system_entry_date=_datetime(elem, "SystemEntryDate", ns) or datetime(2000, 1, 1),
        source_id=_t(elem, "SourceID", ns),
        eac_code=_t(elem, "EACCode", ns),
        customer_id=_t(elem, "CustomerID", ns),
        lines=lines,
        document_totals=_parse_document_totals(elem, ns),
    )


def _parse_working_documents(
    source_docs: etree._Element | None, ns: str
) -> tuple[list[WorkingDocument], SectionTotals | None]:
    if source_docs is None:
        return [], None
    wd = _find(source_docs, "WorkingDocuments", ns)
    if wd is None:
        return [], None
    totals = _parse_section_totals(wd, ns)
    docs = [_parse_working_doc(e, ns) for e in _findall(wd, "WorkDocument", ns)]
    return docs, totals


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def parse_saft_file(file_path: str) -> SaftData:
    """Parse a SAF-T PT XML file into a SaftData model.

    Args:
        file_path: Absolute path to the XML file.

    Returns:
        Fully parsed SaftData with all sections populated.

    Raises:
        SaftParseError: If the file cannot be parsed.
    """
    ns = detect_namespace(file_path)

    try:
        tree = etree.parse(file_path)  # noqa: S320 -- trusted local files only
    except etree.XMLSyntaxError as e:
        raise SaftParseError(f"Invalid XML: {e}") from e

    root = tree.getroot()
    metadata = _parse_header(root, ns, file_path)

    master_files = _find(root, "MasterFiles", ns)
    customers = _parse_customers(master_files, ns)
    suppliers = _parse_suppliers(master_files, ns)
    products = _parse_products(master_files, ns)
    tax_table = _parse_tax_table(master_files, ns)

    source_docs = _find(root, "SourceDocuments", ns)
    invoices, si_totals = _parse_invoices(source_docs, ns)
    payments, pay_totals = _parse_payments(source_docs, ns)
    movements, mov_totals = _parse_movements(source_docs, ns)
    working_docs, wd_totals = _parse_working_documents(source_docs, ns)

    # Compute record counts
    metadata.record_counts = {
        "customers": len(customers),
        "suppliers": len(suppliers),
        "products": len(products),
        "tax_entries": len(tax_table),
        "invoices": len(invoices),
        "payments": len(payments),
        "movements": len(movements),
        "working_documents": len(working_docs),
    }

    return SaftData(
        metadata=metadata,
        customers=customers,
        suppliers=suppliers,
        products=products,
        tax_table=tax_table,
        invoices=invoices,
        sales_invoices_totals=si_totals,
        payments=payments,
        payments_totals=pay_totals,
        movement_of_goods=movements,
        movement_of_goods_totals=mov_totals,
        working_documents=working_docs,
        working_documents_totals=wd_totals,
    )
