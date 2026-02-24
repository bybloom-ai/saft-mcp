"""Custom exception hierarchy for SAF-T MCP server."""


class SaftError(Exception):
    """Base exception for all SAF-T MCP errors."""


class SaftParseError(SaftError):
    """File cannot be parsed as valid XML."""


class SaftSchemaError(SaftError):
    """File parses as XML but does not match expected SAF-T structure."""


class SaftNoFileLoadedError(SaftError):
    """Tool called without a loaded SAF-T file."""


class SaftFileTooLargeError(SaftError):
    """File exceeds memory limits for full parse mode."""


class SaftEncodingError(SaftError):
    """File encoding detection failed or contains invalid characters."""


class SaftStreamingUnsupportedError(SaftError):
    """Tool requires full parse mode but file was loaded in streaming mode."""
