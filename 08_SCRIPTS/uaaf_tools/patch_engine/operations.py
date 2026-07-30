"""
Official patch operations for the UAAF Patch Engine.

This module implements the six operation types frozen by the Patch Engine
architecture:

- ReplaceText
- InsertBefore
- InsertAfter
- ReplaceMethodBody
- EnsureImport
- WriteFile

The module contains no file-system commit logic. Each handler receives the
current in-memory content and returns an OperationOutput. Backup creation,
validation, writing, and rollback remain the responsibility of PatchEngine.
"""

from __future__ import annotations

import ast
import textwrap
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .exceptions import (
    DuplicateTargetError,
    PatchAlreadyAppliedError,
    PatchConflictError,
    PatchOperationError,
    TargetNotFoundError,
    UnsupportedOperationError,
)
from .models import PatchOperation, PatchOperationType


@dataclass(frozen=True, slots=True)
class OperationOutput:
    """Result returned by one in-memory patch operation."""

    content: str
    changed: bool
    message: str


class BasePatchOperation(ABC):
    """Base contract implemented by every Patch Engine operation."""

    operation_type: PatchOperationType

    def apply(
        self,
        *,
        content: str,
        operation: PatchOperation,
        target_file: Path,
    ) -> OperationOutput:
        """Validate and apply one operation to in-memory content."""

        if operation.operation_type is not self.operation_type:
            raise PatchOperationError(
                f"Handler '{type(self).__name__}' cannot execute operation type "
                f"'{operation.operation_type.value}'."
            )

        if not isinstance(operation.parameters, Mapping):
            raise PatchOperationError(
                f"Operation '{operation.operation_id}' parameters must be a mapping."
            )

        return self._apply(
            content=content,
            operation=operation,
            target_file=target_file,
        )

    @abstractmethod
    def _apply(
        self,
        *,
        content: str,
        operation: PatchOperation,
        target_file: Path,
    ) -> OperationOutput:
        """Apply the concrete operation."""


def _require_string(
    operation: PatchOperation,
    parameter_name: str,
    *,
    allow_empty: bool = False,
) -> str:
    """Return a required string operation parameter."""

    value = operation.parameters.get(parameter_name)

    if not isinstance(value, str):
        raise PatchOperationError(
            f"Operation '{operation.operation_id}' requires string parameter "
            f"'{parameter_name}'."
        )

    if not allow_empty and not value:
        raise PatchOperationError(
            f"Operation '{operation.operation_id}' requires non-empty parameter "
            f"'{parameter_name}'."
        )

    return value


def _optional_bool(
    operation: PatchOperation,
    parameter_name: str,
    default: bool,
) -> bool:
    """Return an optional boolean operation parameter."""

    value: Any = operation.parameters.get(parameter_name, default)

    if not isinstance(value, bool):
        raise PatchOperationError(
            f"Operation '{operation.operation_id}' parameter "
            f"'{parameter_name}' must be boolean."
        )

    return value


def _match_count(content: str, target: str) -> int:
    """Count exact non-overlapping target occurrences."""

    return content.count(target)


def _require_single_match(
    *,
    operation: PatchOperation,
    content: str,
    target: str,
    target_label: str,
) -> None:
    """Require exactly one target occurrence."""

    occurrences = _match_count(content, target)

    if occurrences == 0:
        raise TargetNotFoundError(
            f"Operation '{operation.operation_id}' could not find "
            f"{target_label}."
        )

    if occurrences > 1:
        raise DuplicateTargetError(
            f"Operation '{operation.operation_id}' found {occurrences} "
            f"matches for {target_label}; exactly one is required."
        )


class ReplaceTextOperation(BasePatchOperation):
    """Replace one exact text fragment with another."""

    operation_type = PatchOperationType.REPLACE_TEXT

    def _apply(
        self,
        *,
        content: str,
        operation: PatchOperation,
        target_file: Path,
    ) -> OperationOutput:
        old_text = _require_string(operation, "old_text")
        new_text = _require_string(
            operation,
            "new_text",
            allow_empty=True,
        )

        if old_text == new_text:
            return OperationOutput(
                content=content,
                changed=False,
                message="Replacement source and destination are identical.",
            )

        occurrences = _match_count(content, old_text)

        if occurrences == 0:
            if new_text and new_text in content:
                raise PatchAlreadyAppliedError(
                    f"Operation '{operation.operation_id}' appears to be "
                    "already applied."
                )

            raise TargetNotFoundError(
                f"Operation '{operation.operation_id}' could not find "
                "the requested old_text."
            )

        if occurrences > 1:
            raise DuplicateTargetError(
                f"Operation '{operation.operation_id}' found {occurrences} "
                "old_text matches; exactly one is required."
            )

        updated = content.replace(old_text, new_text, 1)

        return OperationOutput(
            content=updated,
            changed=True,
            message=f"Text replaced in '{target_file}'.",
        )


class InsertBeforeOperation(BasePatchOperation):
    """Insert content immediately before one exact anchor."""

    operation_type = PatchOperationType.INSERT_BEFORE

    def _apply(
        self,
        *,
        content: str,
        operation: PatchOperation,
        target_file: Path,
    ) -> OperationOutput:
        anchor = _require_string(operation, "anchor")
        insertion = _require_string(
            operation,
            "content",
            allow_empty=True,
        )

        if not insertion:
            return OperationOutput(
                content=content,
                changed=False,
                message="Insertion content is empty; no change was required.",
            )

        combined = insertion + anchor

        if combined in content:
            return OperationOutput(
                content=content,
                changed=False,
                message="Requested content already exists before the anchor.",
            )

        _require_single_match(
            operation=operation,
            content=content,
            target=anchor,
            target_label="the insert-before anchor",
        )

        updated = content.replace(anchor, combined, 1)

        return OperationOutput(
            content=updated,
            changed=True,
            message=f"Content inserted before anchor in '{target_file}'.",
        )


class InsertAfterOperation(BasePatchOperation):
    """Insert content immediately after one exact anchor."""

    operation_type = PatchOperationType.INSERT_AFTER

    def _apply(
        self,
        *,
        content: str,
        operation: PatchOperation,
        target_file: Path,
    ) -> OperationOutput:
        anchor = _require_string(operation, "anchor")
        insertion = _require_string(
            operation,
            "content",
            allow_empty=True,
        )

        if not insertion:
            return OperationOutput(
                content=content,
                changed=False,
                message="Insertion content is empty; no change was required.",
            )

        combined = anchor + insertion

        if combined in content:
            return OperationOutput(
                content=content,
                changed=False,
                message="Requested content already exists after the anchor.",
            )

        _require_single_match(
            operation=operation,
            content=content,
            target=anchor,
            target_label="the insert-after anchor",
        )

        updated = content.replace(anchor, combined, 1)

        return OperationOutput(
            content=updated,
            changed=True,
            message=f"Content inserted after anchor in '{target_file}'.",
        )


class ReplaceMethodBodyOperation(BasePatchOperation):
    """Replace a Python function or method body using AST source locations."""

    operation_type = PatchOperationType.REPLACE_METHOD_BODY

    def _apply(
        self,
        *,
        content: str,
        operation: PatchOperation,
        target_file: Path,
    ) -> OperationOutput:
        method_name = _require_string(operation, "method_name")
        new_body = _require_string(operation, "new_body")
        class_name_value = operation.parameters.get("class_name")

        if class_name_value is not None and not isinstance(class_name_value, str):
            raise PatchOperationError(
                f"Operation '{operation.operation_id}' parameter "
                "'class_name' must be a string or None."
            )

        class_name = class_name_value or None

        try:
            tree = ast.parse(content, filename=str(target_file))
        except SyntaxError as error:
            raise PatchConflictError(
                f"Operation '{operation.operation_id}' cannot inspect invalid "
                f"Python source in '{target_file}': {error}"
            ) from error

        candidates = self._find_candidates(
            tree=tree,
            method_name=method_name,
            class_name=class_name,
        )

        if not candidates:
            location = (
                f"class '{class_name}'" if class_name else "module scope"
            )
            raise TargetNotFoundError(
                f"Operation '{operation.operation_id}' could not find "
                f"method '{method_name}' in {location}."
            )

        if len(candidates) > 1:
            raise DuplicateTargetError(
                f"Operation '{operation.operation_id}' found multiple "
                f"definitions for method '{method_name}'."
            )

        function_node = candidates[0]

        if not function_node.body:
            raise PatchConflictError(
                f"Method '{method_name}' has no replaceable body."
            )

        body_start = function_node.body[0].lineno - 1
        body_end = function_node.end_lineno

        if body_end is None:
            raise PatchConflictError(
                f"Python AST did not provide an end line for '{method_name}'."
            )

        source_lines = content.splitlines(keepends=True)
        indentation = " " * (function_node.col_offset + 4)
        replacement_lines = self._format_body(
            new_body=new_body,
            indentation=indentation,
            newline=self._detect_newline(content),
        )

        original_body = "".join(source_lines[body_start:body_end])
        replacement_body = "".join(replacement_lines)

        if original_body == replacement_body:
            return OperationOutput(
                content=content,
                changed=False,
                message=f"Method body for '{method_name}' already matches.",
            )

        updated_lines = (
            source_lines[:body_start]
            + replacement_lines
            + source_lines[body_end:]
        )
        updated = "".join(updated_lines)

        return OperationOutput(
            content=updated,
            changed=True,
            message=(
                f"Body of method '{method_name}' replaced in "
                f"'{target_file}'."
            ),
        )

    @staticmethod
    def _find_candidates(
        *,
        tree: ast.Module,
        method_name: str,
        class_name: str | None,
    ) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        candidates: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

        if class_name is None:
            for node in tree.body:
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == method_name
                ):
                    candidates.append(node)

            return candidates

        matching_classes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ]

        if len(matching_classes) > 1:
            raise DuplicateTargetError(
                f"Multiple classes named '{class_name}' were found."
            )

        if not matching_classes:
            return candidates

        for node in matching_classes[0].body:
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == method_name
            ):
                candidates.append(node)

        return candidates

    @staticmethod
    def _format_body(
        *,
        new_body: str,
        indentation: str,
        newline: str,
    ) -> list[str]:
        normalized = textwrap.dedent(new_body).strip("\r\n")

        if not normalized.strip():
            raise PatchOperationError(
                "ReplaceMethodBody requires a non-empty Python body."
            )

        logical_lines = normalized.splitlines()
        formatted = [
            f"{indentation}{line}{newline}" if line else newline
            for line in logical_lines
        ]

        return formatted

    @staticmethod
    def _detect_newline(content: str) -> str:
        return "\r\n" if "\r\n" in content else "\n"


class EnsureImportOperation(BasePatchOperation):
    """Ensure that one exact Python import statement exists."""

    operation_type = PatchOperationType.ENSURE_IMPORT

    def _apply(
        self,
        *,
        content: str,
        operation: PatchOperation,
        target_file: Path,
    ) -> OperationOutput:
        import_statement = _require_string(
            operation,
            "import_statement",
        ).strip()

        self._validate_import_statement(
            operation=operation,
            import_statement=import_statement,
        )

        existing_lines = {
            line.strip()
            for line in content.splitlines()
            if line.strip()
        }

        if import_statement in existing_lines:
            return OperationOutput(
                content=content,
                changed=False,
                message=f"Import already exists in '{target_file}'.",
            )

        newline = "\r\n" if "\r\n" in content else "\n"

        try:
            tree = ast.parse(content, filename=str(target_file))
        except SyntaxError as error:
            raise PatchConflictError(
                f"Operation '{operation.operation_id}' cannot inspect invalid "
                f"Python source in '{target_file}': {error}"
            ) from error

        insertion_index = self._find_insertion_index(tree)
        source_lines = content.splitlines(keepends=True)
        import_line = import_statement + newline

        source_lines.insert(insertion_index, import_line)
        updated = "".join(source_lines)

        return OperationOutput(
            content=updated,
            changed=True,
            message=f"Import ensured in '{target_file}'.",
        )

    @staticmethod
    def _validate_import_statement(
        *,
        operation: PatchOperation,
        import_statement: str,
    ) -> None:
        try:
            import_tree = ast.parse(import_statement)
        except SyntaxError as error:
            raise PatchOperationError(
                f"Operation '{operation.operation_id}' defines an invalid "
                f"import statement: {error}"
            ) from error

        if (
            len(import_tree.body) != 1
            or not isinstance(import_tree.body[0], (ast.Import, ast.ImportFrom))
        ):
            raise PatchOperationError(
                f"Operation '{operation.operation_id}' parameter "
                "'import_statement' must contain exactly one import."
            )

    @staticmethod
    def _find_insertion_index(tree: ast.Module) -> int:
        """Return a zero-based source-line insertion index."""

        insertion_line = 0
        body = tree.body
        index = 0

        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            insertion_line = body[0].end_lineno or body[0].lineno
            index = 1

        while index < len(body):
            node = body[index]

            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "__future__"
            ):
                insertion_line = node.end_lineno or node.lineno
                index += 1
                continue

            break

        return insertion_line


class WriteFileOperation(BasePatchOperation):
    """Create a file or replace its complete in-memory content."""

    operation_type = PatchOperationType.WRITE_FILE

    def _apply(
        self,
        *,
        content: str,
        operation: PatchOperation,
        target_file: Path,
    ) -> OperationOutput:
        new_content = _require_string(
            operation,
            "content",
            allow_empty=True,
        )
        overwrite = _optional_bool(
            operation,
            "overwrite",
            False,
        )
        target_exists = target_file.exists()

        if target_exists and not overwrite:
            if content == new_content:
                return OperationOutput(
                    content=content,
                    changed=False,
                    message=f"File '{target_file}' already has requested content.",
                )

            raise PatchConflictError(
                f"Operation '{operation.operation_id}' cannot overwrite "
                f"existing file '{target_file}' because overwrite is disabled."
            )

        if content == new_content:
            return OperationOutput(
                content=content,
                changed=False,
                message=f"File '{target_file}' already has requested content.",
            )

        return OperationOutput(
            content=new_content,
            changed=True,
            message=(
                f"File '{target_file}' "
                f"{'overwritten' if target_exists else 'created'}."
            ),
        )


OPERATION_REGISTRY: dict[
    PatchOperationType,
    BasePatchOperation,
] = {
    PatchOperationType.REPLACE_TEXT: ReplaceTextOperation(),
    PatchOperationType.INSERT_BEFORE: InsertBeforeOperation(),
    PatchOperationType.INSERT_AFTER: InsertAfterOperation(),
    PatchOperationType.REPLACE_METHOD_BODY: ReplaceMethodBodyOperation(),
    PatchOperationType.ENSURE_IMPORT: EnsureImportOperation(),
    PatchOperationType.WRITE_FILE: WriteFileOperation(),
}


def get_operation_handler(
    operation_type: PatchOperationType,
) -> BasePatchOperation:
    """Return the registered handler for an official operation type."""

    try:
        return OPERATION_REGISTRY[operation_type]
    except KeyError as error:
        value = getattr(operation_type, "value", operation_type)
        raise UnsupportedOperationError(
            f"Unsupported Patch Engine operation type: {value!r}."
        ) from error


__all__ = [
    "OperationOutput",
    "BasePatchOperation",
    "ReplaceTextOperation",
    "InsertBeforeOperation",
    "InsertAfterOperation",
    "ReplaceMethodBodyOperation",
    "EnsureImportOperation",
    "WriteFileOperation",
    "OPERATION_REGISTRY",
    "get_operation_handler",
]