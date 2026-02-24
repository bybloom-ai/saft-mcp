"""Tests for hash chain verification."""


from saft_mcp.validators.hash_chain import extract_number, extract_series


class TestExtractSeries:
    def test_standard_format(self):
        assert extract_series("FT A/1") == "FT A"

    def test_multi_part_series(self):
        assert extract_series("FT JOSEFINAS/123") == "FT JOSEFINAS"

    def test_credit_note(self):
        assert extract_series("NC A/5") == "NC A"

    def test_whitespace_stripped(self):
        assert extract_series("  FT A/1  ") == "FT A"


class TestExtractNumber:
    def test_standard_format(self):
        assert extract_number("FT A/1") == 1

    def test_large_number(self):
        assert extract_number("FT A/999") == 999

    def test_single_digit(self):
        assert extract_number("NC A/3") == 3


class TestVerifyHashChain:
    """Hash chain tests require real Invoice objects.

    These are tested via the integration tests that use parsed real data.
    """

    pass
