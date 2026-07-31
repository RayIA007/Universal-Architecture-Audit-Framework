"""
UAAF Core Exceptions.
"""
from __future__ import annotations


class UAAFError(Exception):
    """Base exception for all UAAF errors."""
    pass


class AuditError(UAAFError):
    """Exception raised during audit execution."""
    pass


class PluginError(UAAFError):
    """Exception raised during plugin operations."""
    pass


class ValidationError(UAAFError):
    """Exception raised during validation."""
    pass


__all__ = [
    "UAAFError",
    "AuditError",
    "PluginError",
    "ValidationError",
]