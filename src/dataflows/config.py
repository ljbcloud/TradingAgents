"""
Configuration management for dataflows module.

Provides runtime configuration access for data vendor settings,
allowing the DEFAULT_CONFIG to be overridden when needed.
"""

import default_config

# Use default config but allow it to be overridden
_config: dict | None = None


def initialize_config() -> None:
    """Initialize the configuration with default values."""
    global _config
    if _config is None:
        _config = default_config.DEFAULT_CONFIG.copy()


def set_config(config: dict) -> None:
    """Update the configuration with custom values."""
    global _config
    if _config is None:
        _config = default_config.DEFAULT_CONFIG.copy()
    _config.update(config)


def get_config() -> dict:
    """Get the current configuration."""
    if _config is None:
        initialize_config()
    return _config.copy()


# Initialize with default config
initialize_config()
