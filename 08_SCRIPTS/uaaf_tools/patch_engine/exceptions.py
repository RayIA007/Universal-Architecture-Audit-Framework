"""
Official exceptions for the UAAF Patch Engine.

This module centralizes every exception raised by the Patch Engine.
It contains no execution logic.
"""

from __future__ import annotations


class PatchEngineError(Exception):
    """Base exception for all Patch Engine errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class PatchValidationError(PatchEngineError):
    """Raised when a PatchPlan is invalid."""


class PatchExecutionError(PatchEngineError):
    """Raised when the Patch Engine cannot complete execution."""


class PatchOperationError(PatchEngineError):
    """Raised when a patch operation fails."""


class PatchFileError(PatchEngineError):
    """Raised when a file operation fails."""


class PatchBackupError(PatchEngineError):
    """Raised when a backup cannot be created."""


class PatchRollbackError(PatchEngineError):
    """Raised when rollback cannot restore the previous state."""


class PatchAstValidationError(PatchValidationError):
    """Raised when AST validation fails."""


class PatchCompilationError(PatchValidationError):
    """Raised when py_compile validation fails."""


class UnsupportedOperationError(PatchOperationError):
    """Raised when an unsupported patch operation is requested."""


class TargetNotFoundError(PatchOperationError):
    """Raised when the target text or element cannot be located."""


class DuplicateTargetError(PatchOperationError):
    """Raised when an operation matches more than one target unexpectedly."""


class PatchAlreadyAppliedError(PatchOperationError):
    """Raised when a patch has already been applied."""


class PatchConflictError(PatchOperationError):
    """Raised when the current file state conflicts with the Patch Plan."""


class InvalidPatchStateError(PatchExecutionError):
    """Raised when the Patch Engine enters an invalid internal state."""


class PatchIntegrityError(PatchExecutionError):
    """Raised when file integrity cannot be guaranteed after execution."""


class BackupNotFoundError(PatchRollbackError):
    """Raised when a required backup cannot be located."""


class RestoreFailedError(PatchRollbackError):
    """Raised when restoring a backup fails."""


class PatchPermissionError(PatchFileError):
    """Raised when file permissions prevent an operation."""


class PatchReadError(PatchFileError):
    """Raised when a file cannot be read."""


class PatchWriteError(PatchFileError):
    """Raised when a file cannot be written."""


class PatchFileNotFoundError(PatchFileError):
    """Raised when the target file does not exist."""