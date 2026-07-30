"""
Data models for the UAAF Patch Engine.

This module contains only the data structures and enumerations used by the
Patch Engine. It does not apply patches, modify files, create backups, or
perform validations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence


class PatchOperationType(str, Enum):
    """Official operation types supported by the Patch Engine."""

    REPLACE_TEXT = "replace_text"
    INSERT_BEFORE = "insert_before"
    INSERT_AFTER = "insert_after"
    REPLACE_METHOD_BODY = "replace_method_body"
    ENSURE_IMPORT = "ensure_import"
    WRITE_FILE = "write_file"


class PatchStatus(str, Enum):
    """Possible execution states for a patch or patch operation."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True, slots=True)
class PatchOperation:
    """Represents one ordered modification within a patch plan.

    Attributes:
        operation_id: Unique identifier of the operation inside the plan.
        operation_type: Type of modification to perform.
        target_file: File affected by the operation.
        parameters: Operation-specific input values.
        description: Human-readable explanation of the modification.
        required: Indicates whether failure must stop the patch plan.
    """

    operation_id: str
    operation_type: PatchOperationType
    target_file: Path
    parameters: Mapping[str, Any] = field(default_factory=dict)
    description: str = ""
    required: bool = True


@dataclass(frozen=True, slots=True)
class PatchPlan:
    """Represents an ordered collection of patch operations.

    Attributes:
        patch_id: Stable and unique identifier of the patch plan.
        name: Human-readable patch name.
        version: Patch plan version.
        description: Purpose of the patch plan.
        operations: Ordered operations to execute.
        create_backups: Indicates whether affected existing files require
            backups before changes are committed.
        validate_python: Indicates whether modified Python files require AST
            and compilation validation.
    """

    patch_id: str
    name: str
    version: str
    description: str
    operations: Sequence[PatchOperation]
    create_backups: bool = True
    validate_python: bool = True


@dataclass(frozen=True, slots=True)
class OperationResult:
    """Represents the result of one patch operation.

    Attributes:
        operation_id: Identifier of the executed operation.
        operation_type: Type of operation executed.
        target_file: File targeted by the operation.
        status: Final status of the operation.
        changed: Indicates whether file content was modified.
        message: Human-readable execution result.
        error: Error description when execution failed.
    """

    operation_id: str
    operation_type: PatchOperationType
    target_file: Path
    status: PatchStatus
    changed: bool
    message: str = ""
    error: str | None = None


@dataclass(frozen=True, slots=True)
class FileChange:
    """Describes the final change state of one affected file.

    Attributes:
        target_file: File evaluated or modified.
        changed: Indicates whether the file was modified.
        created: Indicates whether the file was created by the patch.
        backup_file: Backup path when a backup was created.
        restored: Indicates whether the original file was restored.
    """

    target_file: Path
    changed: bool
    created: bool = False
    backup_file: Path | None = None
    restored: bool = False


@dataclass(frozen=True, slots=True)
class PatchSummary:
    """Provides aggregate execution information for a patch plan.

    Attributes:
        total_operations: Number of operations in the plan.
        successful_operations: Number of successful operations.
        failed_operations: Number of failed operations.
        skipped_operations: Number of skipped operations.
        changed_files: Number of files modified or created.
        backup_files: Number of backups created.
        rolled_back_files: Number of files restored after failure.
    """

    total_operations: int
    successful_operations: int
    failed_operations: int
    skipped_operations: int
    changed_files: int
    backup_files: int
    rolled_back_files: int


@dataclass(frozen=True, slots=True)
class PatchResult:
    """Represents the complete result of executing a patch plan.

    Attributes:
        patch_id: Identifier of the executed patch plan.
        patch_version: Version of the executed patch plan.
        status: Final patch execution status.
        operation_results: Ordered results for every processed operation.
        file_changes: Final state of every affected file.
        summary: Aggregate execution information.
        message: Human-readable final result.
        error: Main error description when execution failed.
    """

    patch_id: str
    patch_version: str
    status: PatchStatus
    operation_results: Sequence[OperationResult]
    file_changes: Sequence[FileChange]
    summary: PatchSummary
    message: str = ""
    error: str | None = None