"""
Public API for the UAAF Patch Engine.

The Patch Engine applies explicit, validated, deterministic, and reversible
changes to project files through structured PatchPlan definitions.
"""

from __future__ import annotations

from .engine import PatchEngine
from .exceptions import (
    BackupNotFoundError,
    DuplicateTargetError,
    InvalidPatchStateError,
    PatchAlreadyAppliedError,
    PatchAstValidationError,
    PatchBackupError,
    PatchCompilationError,
    PatchConflictError,
    PatchEngineError,
    PatchExecutionError,
    PatchFileError,
    PatchFileNotFoundError,
    PatchIntegrityError,
    PatchOperationError,
    PatchPermissionError,
    PatchReadError,
    PatchRollbackError,
    PatchValidationError,
    PatchWriteError,
    RestoreFailedError,
    TargetNotFoundError,
    UnsupportedOperationError,
)
from .models import (
    FileChange,
    OperationResult,
    PatchOperation,
    PatchOperationType,
    PatchPlan,
    PatchResult,
    PatchStatus,
    PatchSummary,
)
from .operations import (
    BasePatchOperation,
    EnsureImportOperation,
    InsertAfterOperation,
    InsertBeforeOperation,
    OperationOutput,
    ReplaceMethodBodyOperation,
    ReplaceTextOperation,
    WriteFileOperation,
    get_operation_handler,
)
from .version import (
    PATCH_ENGINE_NAME,
    VERSION_INFO,
    __version__,
)


__all__ = [
    # Engine
    "PatchEngine",

    # Models
    "FileChange",
    "OperationResult",
    "PatchOperation",
    "PatchOperationType",
    "PatchPlan",
    "PatchResult",
    "PatchStatus",
    "PatchSummary",

    # Operation infrastructure
    "BasePatchOperation",
    "OperationOutput",
    "get_operation_handler",

    # Supported operations
    "ReplaceTextOperation",
    "InsertBeforeOperation",
    "InsertAfterOperation",
    "ReplaceMethodBodyOperation",
    "EnsureImportOperation",
    "WriteFileOperation",

    # Base exceptions
    "PatchEngineError",
    "PatchValidationError",
    "PatchExecutionError",
    "PatchOperationError",
    "PatchFileError",

    # Validation and execution exceptions
    "PatchAstValidationError",
    "PatchCompilationError",
    "UnsupportedOperationError",
    "TargetNotFoundError",
    "DuplicateTargetError",
    "PatchAlreadyAppliedError",
    "PatchConflictError",
    "InvalidPatchStateError",
    "PatchIntegrityError",

    # File, backup, and rollback exceptions
    "PatchBackupError",
    "PatchRollbackError",
    "BackupNotFoundError",
    "RestoreFailedError",
    "PatchPermissionError",
    "PatchReadError",
    "PatchWriteError",
    "PatchFileNotFoundError",

    # Version information
    "PATCH_ENGINE_NAME",
    "VERSION_INFO",
    "__version__",
]