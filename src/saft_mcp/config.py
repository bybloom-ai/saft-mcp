"""Centralized configuration with sensible defaults, overridable via env vars."""

from pydantic_settings import BaseSettings


class SaftMcpSettings(BaseSettings):
    model_config = {"env_prefix": "SAFT_MCP_"}

    # Parser
    streaming_threshold_bytes: int = 50 * 1024 * 1024  # 50 MB
    max_file_size_bytes: int = 500 * 1024 * 1024  # 500 MB
    max_session_memory_bytes: int = 512 * 1024 * 1024  # 512 MB
    encoding_detect_bytes: int = 16 * 1024  # 16 KB for chardet

    # Session
    session_timeout_seconds: int = 1800  # 30 min
    max_concurrent_sessions: int = 5

    # Query defaults
    default_query_limit: int = 50
    max_query_limit: int = 500

    # Progress
    cancellation_check_interval: int = 1000

    # Transport
    transport: str = "stdio"
    http_host: str = "0.0.0.0"
    http_port: int = 8000

    # Rate limiting (HTTP only)
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10

    # XSD
    default_xsd_version: str = "1.04_01"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"


settings = SaftMcpSettings()
