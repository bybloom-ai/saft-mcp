"""Pydantic models for SAF-T PT data structures.

Validated against real SAF-T exports from PHC Corporate (2024/2025).
Field names follow Python conventions; XSD element names are in comments.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SaftType(StrEnum):
    INVOICING = "invoicing"
    ACCOUNTING = "accounting"


class TaxAccountingBasis(StrEnum):
    """TaxAccountingBasis from Header. Determines file type."""

    CONTABILIDADE = "C"  # Accounting SAF-T
    FACTURACAO = "F"  # Full invoicing SAF-T
    PARCIAL = "P"  # Partial invoicing SAF-T (monthly)
    AUTOFACTURACAO = "S"  # Self-billing
    RECIBOS = "R"  # Receipts only
    INTEGRADA = "I"  # Integrated (accounting + invoicing)


# ---------------------------------------------------------------------------
# Shared / reusable models
# ---------------------------------------------------------------------------


class Address(BaseModel):
    """Maps to CompanyAddress, BillingAddress, ShipTo/ShipFrom Address."""

    address_detail: str = ""  # <AddressDetail>
    city: str = ""  # <City>
    postal_code: str = ""  # <PostalCode>
    region: str = ""  # <Region> (present in ShipFrom/ShipTo, absent in BillingAddress)
    country: str = "PT"  # <Country> (can be "Desconhecido" in some vendor exports)


class LineTax(BaseModel):
    """Tax block within a document line. Subset of TaxEntry (no Description)."""

    tax_type: str  # <TaxType>
    tax_country_region: str  # <TaxCountryRegion>
    tax_code: str  # <TaxCode>
    tax_percentage: Decimal  # <TaxPercentage>


class CurrencyAmount(BaseModel):
    """For non-EUR invoices. Nested inside DocumentTotals."""

    currency_code: str  # <CurrencyCode> e.g. "USD"
    currency_amount: Decimal  # <CurrencyAmount>
    exchange_rate: Decimal  # <ExchangeRate>


class DocumentTotals(BaseModel):
    tax_payable: Decimal  # <TaxPayable>
    net_total: Decimal  # <NetTotal>
    gross_total: Decimal  # <GrossTotal>
    currency: CurrencyAmount | None = None  # <Currency>


class SectionTotals(BaseModel):
    """Control totals from each SourceDocuments sub-section."""

    number_of_entries: int  # <NumberOfEntries>
    total_debit: Decimal  # <TotalDebit>
    total_credit: Decimal  # <TotalCredit>


# ---------------------------------------------------------------------------
# Header / Metadata
# ---------------------------------------------------------------------------


class FileMetadata(BaseModel):
    # Direct from Header
    audit_file_version: str  # <AuditFileVersion> e.g. "1.04_01"
    company_id: str  # <CompanyID> e.g. "Braga 510803601"
    tax_registration_number: str  # <TaxRegistrationNumber>
    tax_accounting_basis: str  # <TaxAccountingBasis> F, P, C, S, R, I
    company_name: str  # <CompanyName>
    business_name: str = ""  # <BusinessName>
    company_address: Address = Address()  # <CompanyAddress>
    fiscal_year: int  # <FiscalYear>
    start_date: date  # <StartDate>
    end_date: date  # <EndDate>
    currency_code: str = "EUR"  # <CurrencyCode>
    date_created: date | None = None  # <DateCreated>
    tax_entity: str = ""  # <TaxEntity>
    product_company_tax_id: str = ""  # <ProductCompanyTaxID>
    software_certificate_number: str = ""  # <SoftwareCertificateNumber>
    product_id: str = ""  # <ProductID>
    product_version: str = ""  # <ProductVersion>
    telephone: str = ""  # <Telephone>
    email: str = ""  # <Email>
    website: str = ""  # <Website>
    # Computed by parser
    saft_type: SaftType = SaftType.INVOICING
    file_size_bytes: int = 0
    record_counts: dict[str, int] = {}


# ---------------------------------------------------------------------------
# MasterFiles
# ---------------------------------------------------------------------------


class Customer(BaseModel):
    customer_id: str  # <CustomerID>
    account_id: str = ""  # <AccountID>
    customer_tax_id: str  # <CustomerTaxID>
    company_name: str  # <CompanyName>
    billing_address: Address = Address()  # <BillingAddress>
    self_billing_indicator: int = 0  # <SelfBillingIndicator>


class Supplier(BaseModel):
    supplier_id: str  # <SupplierID>
    account_id: str = ""  # <AccountID>
    supplier_tax_id: str  # <SupplierTaxID>
    company_name: str  # <CompanyName>
    billing_address: Address = Address()  # <BillingAddress>
    self_billing_indicator: int = 0  # <SelfBillingIndicator>


class Product(BaseModel):
    product_type: str  # <ProductType> P, S, O, I, E
    product_code: str  # <ProductCode>
    product_group: str = ""  # <ProductGroup>
    product_description: str  # <ProductDescription>
    product_number_code: str = ""  # <ProductNumberCode>


class TaxEntry(BaseModel):
    """Maps to TaxTable/TaxTableEntry."""

    tax_type: str  # <TaxType>
    tax_country_region: str  # <TaxCountryRegion>
    tax_code: str  # <TaxCode>
    description: str = ""  # <Description>
    tax_percentage: Decimal  # <TaxPercentage>


# ---------------------------------------------------------------------------
# SalesInvoices
# ---------------------------------------------------------------------------


class LineReference(BaseModel):
    """References block on credit note lines."""

    reference: str  # <Reference> e.g. "FR 2024A15/985"
    reason: str = ""  # <Reason>


class InvoiceLine(BaseModel):
    line_number: int  # <LineNumber>
    product_code: str  # <ProductCode>
    product_description: str  # <ProductDescription>
    quantity: Decimal  # <Quantity>
    unit_of_measure: str = ""  # <UnitOfMeasure>
    unit_price: Decimal  # <UnitPrice>
    tax_point_date: date | None = None  # <TaxPointDate>
    references: LineReference | None = None  # <References>
    description: str = ""  # <Description>
    credit_amount: Decimal = Decimal("0")  # <CreditAmount>
    debit_amount: Decimal = Decimal("0")  # <DebitAmount>
    tax: LineTax  # <Tax>
    tax_exemption_reason: str = ""  # <TaxExemptionReason>
    tax_exemption_code: str = ""  # <TaxExemptionCode>
    settlement_amount: Decimal = Decimal("0")  # <SettlementAmount>


class DocumentStatus(BaseModel):
    """Invoice DocumentStatus."""

    invoice_status: str  # <InvoiceStatus> N, A, F, S
    invoice_status_date: datetime  # <InvoiceStatusDate>
    reason: str = ""  # <Reason>
    source_id: str = ""  # <SourceID>
    source_billing: str  # <SourceBilling> P, I, M


class SpecialRegimes(BaseModel):
    """Nested block inside Invoice."""

    self_billing_indicator: int = 0  # <SelfBillingIndicator>
    cash_vat_scheme_indicator: int = 0  # <CashVATSchemeIndicator>
    third_parties_billing_indicator: int = 0  # <ThirdPartiesBillingIndicator>


class Invoice(BaseModel):
    invoice_no: str  # <InvoiceNo> e.g. "FT 2025A1/1"
    atcud: str = ""  # <ATCUD>
    document_status: DocumentStatus  # <DocumentStatus>
    hash: str  # <Hash>
    hash_control: str = ""  # <HashControl>
    invoice_date: date  # <InvoiceDate>
    invoice_type: str  # <InvoiceType> FT, FS, FR, NC, ND
    special_regimes: SpecialRegimes = SpecialRegimes()  # <SpecialRegimes>
    source_id: str = ""  # <SourceID>
    eac_code: str = ""  # <EACCode>
    system_entry_date: datetime  # <SystemEntryDate>
    customer_id: str  # <CustomerID>
    ship_to: Address | None = None  # <ShipTo><Address>
    ship_from: Address | None = None  # <ShipFrom><Address>
    lines: list[InvoiceLine] = []  # <Line>
    document_totals: DocumentTotals  # <DocumentTotals>


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


class SourceDocumentID(BaseModel):
    """Nested element in payment lines linking to the original invoice."""

    originating_on: str  # <OriginatingON>
    invoice_date: date  # <InvoiceDate>


class PaymentLine(BaseModel):
    line_number: int  # <LineNumber>
    source_document_id: SourceDocumentID | None = None  # <SourceDocumentID>
    credit_amount: Decimal = Decimal("0")  # <CreditAmount>
    debit_amount: Decimal = Decimal("0")  # <DebitAmount>
    tax: LineTax | None = None  # <Tax>


class PaymentStatus(BaseModel):
    payment_status: str  # <PaymentStatus> N, A
    payment_status_date: datetime  # <PaymentStatusDate>
    reason: str = ""  # <Reason>
    source_id: str = ""  # <SourceID>
    source_payment: str  # <SourcePayment> P, I, M


class Payment(BaseModel):
    payment_ref_no: str  # <PaymentRefNo>
    atcud: str = ""  # <ATCUD>
    transaction_date: date  # <TransactionDate>
    payment_type: str  # <PaymentType> RG, RC, AC
    system_id: str = ""  # <SystemID>
    document_status: PaymentStatus  # <DocumentStatus>
    source_id: str = ""  # <SourceID>
    system_entry_date: datetime  # <SystemEntryDate>
    customer_id: str  # <CustomerID>
    lines: list[PaymentLine] = []  # <Line>
    document_totals: DocumentTotals  # <DocumentTotals>


# ---------------------------------------------------------------------------
# MovementOfGoods
# ---------------------------------------------------------------------------


class MovementLine(BaseModel):
    line_number: int  # <LineNumber>
    product_code: str  # <ProductCode>
    product_description: str  # <ProductDescription>
    quantity: Decimal  # <Quantity>
    unit_of_measure: str = ""  # <UnitOfMeasure>
    unit_price: Decimal  # <UnitPrice>
    description: str = ""  # <Description>
    credit_amount: Decimal = Decimal("0")  # <CreditAmount>
    debit_amount: Decimal = Decimal("0")  # <DebitAmount>
    tax: LineTax | None = None  # <Tax>


class MovementStatus(BaseModel):
    movement_status: str  # <MovementStatus> N, T, F, A
    movement_status_date: datetime  # <MovementStatusDate>
    reason: str = ""  # <Reason>
    source_id: str = ""  # <SourceID>
    source_billing: str  # <SourceBilling>


class MovementDocument(BaseModel):
    document_number: str  # <DocumentNumber>
    atcud: str = ""  # <ATCUD>
    document_status: MovementStatus  # <DocumentStatus>
    hash: str  # <Hash>
    hash_control: str = ""  # <HashControl>
    movement_date: date  # <MovementDate>
    movement_type: str  # <MovementType> GR, GT, GA
    system_entry_date: datetime  # <SystemEntryDate>
    source_id: str = ""  # <SourceID>
    eac_code: str = ""  # <EACCode>
    customer_id: str  # <CustomerID>
    ship_to: Address | None = None  # <ShipTo><Address>
    ship_from: Address | None = None  # <ShipFrom><Address>
    movement_start_time: datetime | None = None  # <MovementStartTime>
    lines: list[MovementLine] = []  # <Line>
    document_totals: DocumentTotals  # <DocumentTotals>


# ---------------------------------------------------------------------------
# WorkingDocuments
# ---------------------------------------------------------------------------


class WorkingDocumentLine(BaseModel):
    line_number: int  # <LineNumber>
    product_code: str  # <ProductCode>
    product_description: str  # <ProductDescription>
    quantity: Decimal  # <Quantity>
    unit_of_measure: str = ""  # <UnitOfMeasure>
    unit_price: Decimal  # <UnitPrice>
    description: str = ""  # <Description>
    credit_amount: Decimal = Decimal("0")  # <CreditAmount>
    debit_amount: Decimal = Decimal("0")  # <DebitAmount>
    tax: LineTax | None = None  # <Tax>


class WorkingDocumentStatus(BaseModel):
    document_status: str  # <DocumentStatus> N, A, F
    document_status_date: datetime  # <DocumentStatusDate>
    reason: str = ""  # <Reason>
    source_id: str = ""  # <SourceID>
    source_billing: str  # <SourceBilling>


class WorkingDocument(BaseModel):
    document_number: str  # <DocumentNumber>
    atcud: str = ""  # <ATCUD>
    document_status: WorkingDocumentStatus  # <DocumentStatus>
    hash: str  # <Hash>
    hash_control: str = ""  # <HashControl>
    work_date: date  # <WorkDate>
    work_type: str  # <WorkType> FO, OR, PF, etc.
    system_entry_date: datetime  # <SystemEntryDate>
    source_id: str = ""  # <SourceID>
    eac_code: str = ""  # <EACCode>
    customer_id: str  # <CustomerID>
    lines: list[WorkingDocumentLine] = []  # <Line>
    document_totals: DocumentTotals  # <DocumentTotals>


# ---------------------------------------------------------------------------
# Accounting (GeneralLedgerEntries)
# ---------------------------------------------------------------------------


class GeneralLedgerAccount(BaseModel):
    account_id: str  # <AccountID>
    account_description: str  # <AccountDescription>
    opening_debit_balance: Decimal = Decimal("0")
    opening_credit_balance: Decimal = Decimal("0")
    closing_debit_balance: Decimal = Decimal("0")
    closing_credit_balance: Decimal = Decimal("0")
    group_type: str = ""  # GR, GA, GM


class JournalEntryLine(BaseModel):
    record_id: str  # <RecordID>
    account_id: str  # <AccountID>
    description: str = ""  # <Description>
    debit_amount: Decimal = Decimal("0")
    credit_amount: Decimal = Decimal("0")


class JournalEntry(BaseModel):
    journal_id: str  # <JournalID>
    transaction_id: str  # <TransactionID>
    transaction_date: date  # <TransactionDate>
    description: str  # <Description>
    doc_archival_number: str = ""  # <DocArchivalNumber>
    lines: list[JournalEntryLine] = []


# ---------------------------------------------------------------------------
# Top-level container
# ---------------------------------------------------------------------------


class SaftData(BaseModel):
    """Complete parsed SAF-T file."""

    metadata: FileMetadata
    customers: list[Customer] = []
    suppliers: list[Supplier] = []
    products: list[Product] = []
    tax_table: list[TaxEntry] = []
    invoices: list[Invoice] = []
    sales_invoices_totals: SectionTotals | None = None
    payments: list[Payment] = []
    payments_totals: SectionTotals | None = None
    movement_of_goods: list[MovementDocument] = []
    movement_of_goods_totals: SectionTotals | None = None
    working_documents: list[WorkingDocument] = []
    working_documents_totals: SectionTotals | None = None
    # Accounting SAF-T only
    general_ledger_accounts: list[GeneralLedgerAccount] = []
    journals: list[JournalEntry] = []
