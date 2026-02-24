"""Portuguese NIF (tax ID) validation using mod-11 check digit."""

from __future__ import annotations

NIF_TYPES = {
    "1": "individual",
    "2": "individual",
    "3": "individual",
    "45": "company_mainland",
    "5": "company",
    "6": "public_entity",
    "70": "public_entity",
    "71": "public_entity",
    "72": "public_entity",
    "74": "public_entity",
    "75": "public_entity",
    "77": "public_entity",
    "78": "public_entity",
    "79": "public_entity",
    "8": "irregular",
    "90": "internal_commerce",
    "91": "internal_commerce",
    "98": "non_resident",
    "99": "non_resident",
}

SPECIAL_NIFS = {
    "999999990": "consumidor_final",
    "000000000": "placeholder",
}


def validate_nif(nif: str) -> tuple[bool, str]:
    """Validate a Portuguese NIF using mod-11 check digit.

    Returns (is_valid, nif_type_or_error).
    Foreign (non-numeric) tax IDs return (True, "foreign").
    """
    nif = nif.strip()

    if nif in SPECIAL_NIFS:
        return True, SPECIAL_NIFS[nif]

    # Foreign tax IDs are alphanumeric
    if not nif.isdigit():
        return True, "foreign"

    if len(nif) != 9:
        return False, "Portuguese NIF must be exactly 9 digits"

    digits = [int(d) for d in nif]
    weights = [9, 8, 7, 6, 5, 4, 3, 2]
    checksum = sum(d * w for d, w in zip(digits[:8], weights))
    remainder = checksum % 11

    expected_check = 0 if remainder < 2 else 11 - remainder

    if digits[8] != expected_check:
        return False, f"Invalid check digit: expected {expected_check}, got {digits[8]}"

    # Determine type by prefix (longest match first)
    for prefix, nif_type in sorted(NIF_TYPES.items(), key=lambda x: -len(x[0])):
        if nif.startswith(prefix):
            return True, nif_type

    return True, "unknown_type"
