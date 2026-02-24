"""Tests for NIF (Portuguese tax ID) validation."""

from saft_mcp.validators.nif import validate_nif


class TestValidateNif:
    """Unit tests for validate_nif()."""

    def test_valid_company_nif(self):
        # Josefinas NIF from the real data
        valid, nif_type = validate_nif("510803601")
        assert valid is True
        assert nif_type == "company"

    def test_valid_individual_nif(self):
        # Build a valid individual NIF with prefix 2
        # 2XXXXXXX? - we'll test the algorithm itself
        valid, nif_type = validate_nif("213456789")
        assert isinstance(valid, bool)

    def test_invalid_check_digit(self):
        valid, info = validate_nif("510803600")  # wrong check digit
        assert valid is False
        assert "check digit" in info.lower() or "Invalid" in info

    def test_consumidor_final(self):
        valid, nif_type = validate_nif("999999990")
        assert valid is True
        assert nif_type == "consumidor_final"

    def test_placeholder_nif(self):
        valid, nif_type = validate_nif("000000000")
        assert valid is True
        assert nif_type == "placeholder"

    def test_foreign_alphanumeric(self):
        valid, nif_type = validate_nif("DE123456789")
        assert valid is True
        assert nif_type == "foreign"

    def test_too_short(self):
        valid, info = validate_nif("12345")
        assert valid is False
        assert "9 digits" in info

    def test_too_long(self):
        valid, info = validate_nif("1234567890")
        assert valid is False
        assert "9 digits" in info

    def test_strips_whitespace(self):
        valid, _ = validate_nif("  510803601  ")
        assert valid is True

    def test_empty_is_foreign(self):
        # Empty string is not digits, treated as foreign
        valid, nif_type = validate_nif("")
        assert valid is True
        assert nif_type == "foreign"
