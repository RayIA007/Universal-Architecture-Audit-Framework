"""
Execution engine for the UAAF Patch Engine.

This module coordinates PatchPlan execution. It validates plans, loads files,
creates backups, applies registered operations, validates Python files, writes
changes, performs rollback on failure, and returns structured PatchResult
objects.
"""

from __future__ import annotations

import ast
import py_compile
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterable

from .exceptions import (
    PatchAstValidationError,
    PatchBackupError,
    PatchCompilationError,
    PatchEngineError,
    PatchExecutionError,
    PatchFileNotFoundError,
    PatchPermissionError,
    PatchReadError,
    PatchRollbackError,
    PatchValidationError,
    PatchWriteError,
    RestoreFailedError,
)
from .models import (
    FileChange,
    OperationResult,
    PatchOperation,
    PatchPlan,
    PatchResult,
    PatchStatus,
    PatchSummary,
)
from .operations import get_operation_handler


@dataclass(slots=True)
class _FileState:
    """Internal mutable state for one file during patch execution."""

    target_file: Path
    original_content: str
    current_content: str
    existed_before: bool
    changed: bool = False
    backup_file: Path | None = None
    restored: bool = False


class PatchEngine:
    """Coordinates safe and deterministic execution of Patch Plans."""

    def execute(self, patch_plan: PatchPlan) -> PatchResult:
        """Execute one Patch Plan.

        Args:
            patch_plan: Valid Patch Plan to execute.

        Returns:
            Structured execution result.
        """
        started_at = perf_counter()
        operation_results: list[OperationResult] = []
        file_states: dict[Path, _FileState] = {}

        try:
            self._validate_patch_plan(patch_plan)
            file_states = self._load_file_states(patch_plan.operations)

            if patch_plan.create_backups:
                self._create_backups(file_states.values())

            for operation in patch_plan.operations:
                result = self._execute_operation(
                    operation=operation,
                    file_state=file_states[operation.target_file],
                )
                operation_results.append(result)

                if result.status is PatchStatus.FAILED and operation.required:
                    raise PatchExecutionError(
                        f"Required operation '{operation.operation_id}' failed."
                    )

            if patch_plan.validate_python:
                self._validate_modified_python_files(file_states.values())

            self._write_changed_files(file_states.values())

            elapsed_seconds = perf_counter() - started_at

            return self._build_patch_result(
                patch_plan=patch_plan,
                status=PatchStatus.SUCCESS,
                operation_results=operation_results,
                file_states=file_states.values(),
                message=(
                    "Patch Plan executed successfully "
                    f"in {elapsed_seconds:.4f} seconds."
                ),
            )

        except PatchEngineError as error:
            rollback_error = self._rollback_safely(file_states.values())

            if rollback_error is not None:
                final_error = (
                    f"{error} Rollback also failed: {rollback_error}"
                )
            else:
                final_error = str(error)

            return self._build_patch_result(
                patch_plan=patch_plan,
                status=PatchStatus.FAILED,
                operation_results=operation_results,
                file_states=file_states.values(),
                message="Patch Plan execution failed.",
                error=final_error,
            )

        except Exception as error:
            rollback_error = self._rollback_safely(file_states.values())

            final_error = f"Unexpected Patch Engine failure: {error}"

            if rollback_error is not None:
                final_error += f" Rollback also failed: {rollback_error}"

            return self._build_patch_result(
                patch_plan=patch_plan,
                status=PatchStatus.FAILED,
                operation_results=operation_results,
                file_states=file_states.values(),
                message="Patch Plan execution failed unexpectedly.",
                error=final_error,
            )
    def _validate_patch_plan(self, patch_plan: PatchPlan) -> None:
        """Validate the structure and consistency of a Patch Plan.

        Args:
            patch_plan: Patch Plan to validate.

        Raises:
            PatchValidationError: If the Patch Plan is invalid.
        """
        if not isinstance(patch_plan, PatchPlan):
            raise PatchValidationError(
                "Patch Engine requires a PatchPlan instance."
            )

        if not patch_plan.patch_id.strip():
            raise PatchValidationError(
                "Patch Plan must define a non-empty patch_id."
            )

        if not patch_plan.name.strip():
            raise PatchValidationError(
                f"Patch Plan '{patch_plan.patch_id}' must define a name."
            )

        if not patch_plan.version.strip():
            raise PatchValidationError(
                f"Patch Plan '{patch_plan.patch_id}' must define a version."
            )

        if not patch_plan.operations:
            raise PatchValidationError(
                f"Patch Plan '{patch_plan.patch_id}' contains no operations."
            )

        operation_ids: set[str] = set()

        for operation in patch_plan.operations:
            if not isinstance(operation, PatchOperation):
                raise PatchValidationError(
                    f"Patch Plan '{patch_plan.patch_id}' contains an invalid "
                    "operation object."
                )

            if not operation.operation_id.strip():
                raise PatchValidationError(
                    "Every PatchOperation must define a non-empty operation_id."
                )

            if operation.operation_id in operation_ids:
                raise PatchValidationError(
                    f"Duplicate operation_id '{operation.operation_id}' "
                    f"in Patch Plan '{patch_plan.patch_id}'."
                )

            operation_ids.add(operation.operation_id)

            if not isinstance(operation.target_file, Path):
                raise PatchValidationError(
                    f"Operation '{operation.operation_id}' target_file "
                    "must be a pathlib.Path instance."
                )

            if not operation.target_file.name:
                raise PatchValidationError(
                    f"Operation '{operation.operation_id}' defines an "
                    "invalid target file."
                )

            get_operation_handler(operation.operation_type)

    def _load_file_states(
        self,
        operations: Iterable[PatchOperation],
    ) -> dict[Path, _FileState]:
        """Load the initial state of every file referenced by operations.

        Args:
            operations: Patch operations whose target files must be loaded.

        Returns:
            Mutable state indexed by target file.

        Raises:
            PatchFileNotFoundError: If a required target file does not exist.
            PatchPermissionError: If a target file cannot be accessed.
            PatchReadError: If file content cannot be read.
        """
        file_states: dict[Path, _FileState] = {}

        for operation in operations:
            target_file = operation.target_file

            if target_file in file_states:
                continue

            existed_before = target_file.exists()

            if not existed_before:
                if operation.operation_type.value != "write_file":
                    raise PatchFileNotFoundError(
                        f"Target file '{target_file}' does not exist."
                    )

                file_states[target_file] = _FileState(
                    target_file=target_file,
                    original_content="",
                    current_content="",
                    existed_before=False,
                )
                continue

            if not target_file.is_file():
                raise PatchReadError(
                    f"Target path '{target_file}' is not a regular file."
                )

            try:
                original_content = target_file.read_text(encoding="utf-8")
            except PermissionError as error:
                raise PatchPermissionError(
                    f"Permission denied while reading '{target_file}'."
                ) from error
            except OSError as error:
                raise PatchReadError(
                    f"Unable to read target file '{target_file}': {error}"
                ) from error

            file_states[target_file] = _FileState(
                target_file=target_file,
                original_content=original_content,
                current_content=original_content,
                existed_before=True,
            )

        return file_states
    def _create_backups(
        self,
        file_states: Iterable[_FileState],
    ) -> None:
        """Create backup files for every existing target file."""

        for file_state in file_states:
            if not file_state.existed_before:
                continue

            backup_file = file_state.target_file.with_suffix(
                file_state.target_file.suffix + ".bak"
            )

            try:
                shutil.copy2(file_state.target_file, backup_file)
            except OSError as error:
                raise PatchBackupError(
                    f"Unable to create backup for "
                    f"'{file_state.target_file}': {error}"
                ) from error

            file_state.backup_file = backup_file

    def _execute_operation(
        self,
        *,
        operation: PatchOperation,
        file_state: _FileState,
    ) -> OperationResult:
        """Execute one PatchOperation."""

        handler = get_operation_handler(operation.operation_type)

        try:
            output = handler.apply(
                content=file_state.current_content,
                operation=operation,
                target_file=file_state.target_file,
            )

            file_state.current_content = output.content

            if output.changed:
                file_state.changed = True

            return OperationResult(
                operation_id=operation.operation_id,
                operation_type=operation.operation_type,
                target_file=file_state.target_file,
                status=PatchStatus.SUCCESS,
                changed=output.changed,
                message=output.message,
            )

        except PatchEngineError as error:
            return OperationResult(
                operation_id=operation.operation_id,
                operation_type=operation.operation_type,
                target_file=file_state.target_file,
                status=PatchStatus.FAILED,
                changed=False,
                message="Operation failed.",
                error=str(error),
            )

        except Exception as error:
            return OperationResult(
                operation_id=operation.operation_id,
                operation_type=operation.operation_type,
                target_file=file_state.target_file,
                status=PatchStatus.FAILED,
                changed=False,
                message="Unexpected operation failure.",
                error=str(error),
            )

    def _validate_modified_python_files(
        self,
        file_states: Iterable[_FileState],
    ) -> None:
        """Validate modified Python files using AST and py_compile."""

        for file_state in file_states:
            if not file_state.changed:
                continue

            if file_state.target_file.suffix != ".py":
                continue

            try:
                ast.parse(file_state.current_content)
            except SyntaxError as error:
                raise PatchAstValidationError(
                    f"AST validation failed for "
                    f"'{file_state.target_file}': {error}"
                ) from error

            temporary_file: Path | None = None

            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".py",
                    encoding="utf-8",
                    delete=False,
                ) as temp_file:
                    temp_file.write(file_state.current_content)
                    temporary_file = Path(temp_file.name)

                py_compile.compile(
                    str(temporary_file),
                    doraise=True,
                )

            except py_compile.PyCompileError as error:
                raise PatchCompilationError(
                    f"Compilation validation failed for "
                    f"'{file_state.target_file}': {error}"
                ) from error

            finally:
                if (
                    temporary_file is not None
                    and temporary_file.exists()
                ):
                    temporary_file.unlink()
    def _write_changed_files(
        self,
        file_states: Iterable[_FileState],
    ) -> None:
        """Persist modified file contents."""

        for file_state in file_states:
            if not file_state.changed:
                continue

            try:
                file_state.target_file.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                file_state.target_file.write_text(
                    file_state.current_content,
                    encoding="utf-8",
                )

            except PermissionError as error:
                raise PatchPermissionError(
                    f"Permission denied while writing "
                    f"'{file_state.target_file}'."
                ) from error

            except OSError as error:
                raise PatchWriteError(
                    f"Unable to write '{file_state.target_file}': {error}"
                ) from error

    def _rollback_safely(
        self,
        file_states: Iterable[_FileState],
    ) -> Exception | None:
        """Attempt to restore the original project state.

        Returns:
            None if rollback succeeds, otherwise the exception raised during
            rollback.
        """

        try:
            for file_state in file_states:
                if not file_state.changed:
                    continue

                if file_state.existed_before:
                    if (
                        file_state.backup_file is None
                        or not file_state.backup_file.exists()
                    ):
                        raise RestoreFailedError(
                            f"Backup for '{file_state.target_file}' "
                            "was not found."
                        )

                    shutil.copy2(
                        file_state.backup_file,
                        file_state.target_file,
                    )

                    file_state.restored = True

                else:
                    if file_state.target_file.exists():
                        file_state.target_file.unlink()

                        file_state.restored = True

            return None

        except Exception as error:
            return PatchRollbackError(str(error))

    def _build_patch_result(
        self,
        *,
        patch_plan: PatchPlan,
        status: PatchStatus,
        operation_results: list[OperationResult],
        file_states: Iterable[_FileState],
        message: str,
        error: str | None = None,
    ) -> PatchResult:
        """Build the final PatchResult."""

        file_changes: list[FileChange] = []

        successful_operations = 0
        failed_operations = 0
        skipped_operations = 0

        changed_files = 0
        backup_files = 0
        rolled_back_files = 0

        for result in operation_results:
            if result.status is PatchStatus.SUCCESS:
                successful_operations += 1

            elif result.status is PatchStatus.FAILED:
                failed_operations += 1

            elif result.status is PatchStatus.SKIPPED:
                skipped_operations += 1

        for state in file_states:
            if state.changed:
                changed_files += 1

            if state.backup_file is not None:
                backup_files += 1

            if state.restored:
                rolled_back_files += 1

            file_changes.append(
                FileChange(
                    target_file=state.target_file,
                    changed=state.changed,
                    created=not state.existed_before,
                    backup_file=state.backup_file,
                    restored=state.restored,
                )
            )

        summary = PatchSummary(
            total_operations=len(operation_results),
            successful_operations=successful_operations,
            failed_operations=failed_operations,
            skipped_operations=skipped_operations,
            changed_files=changed_files,
            backup_files=backup_files,
            rolled_back_files=rolled_back_files,
        )

        return PatchResult(
            patch_id=patch_plan.patch_id,
            patch_version=patch_plan.version,
            status=status,
            operation_results=operation_results,
            file_changes=file_changes,
            summary=summary,
            message=message,
            error=error,
        )


__all__ = [
    "PatchEngine",
]