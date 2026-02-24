"""Encoding detection and BOM handling for SAF-T XML files."""

import re

import chardet

from saft_mcp.config import settings
from saft_mcp.exceptions import SaftEncodingError

# UTF-8 BOM
_BOM_UTF8 = b"\xef\xbb\xbf"
# XML declaration pattern to extract declared encoding
_ENCODING_RE = re.compile(rb'<\?xml[^>]+encoding=["\']([^"\']+)["\']', re.IGNORECASE)


def strip_bom(data: bytes) -> bytes:
    """Strip UTF-8 BOM if present."""
    if data.startswith(_BOM_UTF8):
        return data[len(_BOM_UTF8) :]
    return data


def detect_encoding(file_path: str) -> str:
    """Detect file encoding.

    Strategy:
    1. Read the XML declaration for the declared encoding (fast path).
    2. If no declaration or lxml fails, use chardet on the first 16 KB.
    """
    with open(file_path, "rb") as f:
        header = f.read(settings.encoding_detect_bytes)

    header = strip_bom(header)

    # Try XML declaration first
    match = _ENCODING_RE.search(header[:500])
    if match:
        declared = match.group(1).decode("ascii", errors="replace").strip()
        return _normalize_encoding(declared)

    # Fallback to chardet
    result = chardet.detect(header)
    if result["encoding"] is None:
        raise SaftEncodingError(
            "Could not detect file encoding. "
            "Ensure the file is a valid XML document."
        )

    return _normalize_encoding(result["encoding"])


def _normalize_encoding(encoding: str) -> str:
    """Normalize encoding names to Python codec names."""
    mapping = {
        "windows-1252": "cp1252",
        "win-1252": "cp1252",
        "iso-8859-1": "latin-1",
        "iso-8859-15": "latin-9",
    }
    lower = encoding.lower().strip()
    return mapping.get(lower, lower)
