"""Configuration-related exceptions for F1 Penalty Agent."""

from .base import F1AgentError


class ConfigurationError(F1AgentError):
    """Configuration or environment variable errors.

    Raised when required configuration is missing or invalid.
    """

    error_code = "F1_CFG_001"


class MissingAPIKeyError(ConfigurationError):
    """Required API key is not configured."""

    error_code = "F1_CFG_002"


class InvalidConfigurationError(ConfigurationError):
    """Configuration value is invalid."""

    error_code = "F1_CFG_003"
