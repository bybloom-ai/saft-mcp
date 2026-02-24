"""Tests for the full DOM parser against real SAF-T files."""

from pathlib import Path

from saft_mcp.parser.full_parser import parse_saft_file
from saft_mcp.parser.models import SaftType


class TestFullParserRealData:
    """Test parser against real PHC Corporate SAF-T exports."""

    def test_parse_full_year(self, real_full_year_path: Path) -> None:
        data = parse_saft_file(str(real_full_year_path))

        # Header
        assert data.metadata.company_name == "BLOOMERS, S.A"
        assert data.metadata.tax_registration_number == "510803601"
        assert data.metadata.fiscal_year == 2025
        assert data.metadata.tax_accounting_basis == "F"
        assert data.metadata.saft_type == SaftType.INVOICING
        assert data.metadata.audit_file_version == "1.04_01"
        assert data.metadata.currency_code == "EUR"
        assert data.metadata.company_address.city == "Braga"
        assert data.metadata.product_id.startswith("CS PHC Corporate")

        # MasterFiles
        assert len(data.customers) > 0
        assert len(data.products) > 0
        assert len(data.tax_table) > 0

        # Check a customer has expected structure
        first_customer = data.customers[0]
        assert first_customer.customer_id
        assert first_customer.customer_tax_id
        assert first_customer.company_name

        # Check a product has ProductNumberCode
        first_product = data.products[0]
        assert first_product.product_code
        assert first_product.product_number_code

        # SalesInvoices
        assert len(data.invoices) > 0
        assert data.sales_invoices_totals is not None
        assert data.sales_invoices_totals.number_of_entries == len(data.invoices)

        # Check first invoice structure
        inv = data.invoices[0]
        assert inv.invoice_no
        assert inv.atcud  # ATCUD should be present (post-2023 file)
        assert inv.hash
        assert inv.invoice_type in ("FT", "FR", "NC", "ND", "FS")
        assert inv.system_entry_date
        assert inv.document_status.source_billing
        assert len(inv.lines) > 0

        # Check invoice line
        line = inv.lines[0]
        assert line.product_code
        assert line.quantity > 0
        assert line.tax.tax_type == "IVA"

        # SpecialRegimes should be parsed
        assert inv.special_regimes is not None

        # Payments
        assert len(data.payments) > 0
        pay = data.payments[0]
        assert pay.payment_ref_no
        assert pay.payment_type  # RG in PHC
        assert len(pay.lines) > 0
        # Payment lines should have SourceDocumentID
        pay_line = pay.lines[0]
        assert pay_line.source_document_id is not None
        assert pay_line.source_document_id.originating_on

        # MovementOfGoods
        assert len(data.movement_of_goods) > 0
        mov = data.movement_of_goods[0]
        assert mov.document_number
        assert mov.movement_type

        # Record counts
        assert data.metadata.record_counts["invoices"] == len(data.invoices)
        assert data.metadata.record_counts["customers"] == len(data.customers)

    def test_parse_monthly(self, real_monthly_path: Path) -> None:
        data = parse_saft_file(str(real_monthly_path))

        # Monthly files have TaxAccountingBasis=P
        assert data.metadata.tax_accounting_basis == "P"
        assert data.metadata.saft_type == SaftType.INVOICING

        # Monthly files have customers but may lack products/tax_table
        assert len(data.customers) > 0

        # Should still have invoices
        assert len(data.invoices) > 0

        # Monthly files may not have payments or movements
        # (they're absent from the monthly export)

    def test_document_totals_currency(self, real_full_year_path: Path) -> None:
        """Verify non-EUR invoices have Currency inside DocumentTotals."""
        data = parse_saft_file(str(real_full_year_path))

        # Find invoices with currency info
        currency_invoices = [
            inv for inv in data.invoices
            if inv.document_totals.currency is not None
        ]

        if currency_invoices:
            ci = currency_invoices[0]
            assert ci.document_totals.currency is not None
            assert ci.document_totals.currency.currency_code != "EUR"
            assert ci.document_totals.currency.exchange_rate > 0

    def test_credit_note_references(self, real_full_year_path: Path) -> None:
        """Verify credit note lines have References with original document."""
        data = parse_saft_file(str(real_full_year_path))

        credit_notes = [inv for inv in data.invoices if inv.invoice_type == "NC"]
        if credit_notes:
            nc = credit_notes[0]
            # NC lines should use debit_amount
            for line in nc.lines:
                assert line.debit_amount > 0 or line.credit_amount > 0
            # At least some NC lines should have references
            lines_with_refs = [ln for ln in nc.lines if ln.references is not None]
            assert len(lines_with_refs) > 0
            assert lines_with_refs[0].references.reference  # Original doc number

    def test_cancelled_invoice_has_reason(self, real_full_year_path: Path) -> None:
        """Verify cancelled invoices have a Reason in DocumentStatus."""
        data = parse_saft_file(str(real_full_year_path))

        cancelled = [inv for inv in data.invoices if inv.document_status.invoice_status == "A"]
        if cancelled:
            assert cancelled[0].document_status.reason != ""

    def test_tax_exemption_fields(self, real_full_year_path: Path) -> None:
        """Verify ISE (exempt) lines have TaxExemptionReason and Code."""
        data = parse_saft_file(str(real_full_year_path))

        for inv in data.invoices:
            for line in inv.lines:
                if line.tax.tax_code == "ISE":
                    assert line.tax_exemption_reason != "", (
                        f"Line {line.line_number} in {inv.invoice_no} "
                        f"has ISE tax code but no exemption reason"
                    )
                    assert line.tax_exemption_code != ""
                    return  # Found at least one, test passes
