"""
PATCH-RUNTIME-PIPELINE-COMMIT-0004C

Extend PipelineFailureHandler with terminal failure-state handling.

This commit modifies only pipeline_failure_handler.py. RuntimePipeline remains
unchanged until the next integration commit.
"""

from __future__ import annotations

import ast
import py_compile
import shutil
from datetime import datetime
from pathlib import Path


SCRIPT_FILE = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_FILE.parents[2]

TARGET = (
    PROJECT_ROOT
    / "08_SCRIPTS"
    / "uaaf_core"
    / "runtime"
    / "pipeline_failure_handler.py"
)

METHOD_SOURCE = '    @staticmethod\n    def mark_stopped(\n        *,\n        execution: Any,\n        failed_status: Any,\n        completed_at: Any,\n    ) -> None:\n        """\n        Mark one execution as terminally failed.\n\n        Status and timestamp types remain owned by RuntimePipeline. This\n        handler only applies the terminal state transition, avoiding a\n        dependency on pipeline models and preventing circular imports.\n        """\n        if execution is None:\n            raise TypeError("execution cannot be None.")\n\n        if not hasattr(execution, "status"):\n            raise TypeError(\n                "execution is missing required attribute: status."\n            )\n\n        if not hasattr(execution, "completed_at"):\n            raise TypeError(\n                "execution is missing required attribute: completed_at."\n            )\n\n        if failed_status is None:\n            raise TypeError("failed_status cannot be None.")\n\n        if completed_at is None:\n            raise TypeError("completed_at cannot be None.")\n\n        execution.status = failed_status\n        execution.completed_at = completed_at\n\n'

INSERTION_ANCHOR = (
    "    @staticmethod\n"
    "    def _validate_execution(execution: Any) -> None:\n"
)


def create_backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(
        f"{path.name}.{timestamp}.bak"
    )
    shutil.copy2(path, backup_path)
    return backup_path


def parse_module(source: str) -> ast.Module:
    return ast.parse(source, filename=str(TARGET))


def find_handler_class(tree: ast.Module) -> ast.ClassDef:
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "PipelineFailureHandler"
    ]

    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one PipelineFailureHandler class; "
            f"found {len(matches)}."
        )

    return matches[0]


def has_method(source: str, method_name: str) -> bool:
    tree = parse_module(source)
    handler_class = find_handler_class(tree)

    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == method_name
        for node in handler_class.body
    )


def validate_source(source: str) -> None:
    tree = parse_module(source)
    handler_class = find_handler_class(tree)

    methods = {
        node.name: node
        for node in handler_class.body
        if isinstance(node, ast.FunctionDef)
    }

    required_methods = {
        "handle",
        "mark_stopped",
        "_validate_execution",
    }

    missing = required_methods - methods.keys()
    if missing:
        raise RuntimeError(
            "PipelineFailureHandler is missing methods: "
            f"{', '.join(sorted(missing))}."
        )

    mark_stopped = methods["mark_stopped"]
    argument_names = [
        argument.arg
        for argument in mark_stopped.args.kwonlyargs
    ]

    expected_arguments = [
        "execution",
        "failed_status",
        "completed_at",
    ]

    if argument_names != expected_arguments:
        raise RuntimeError(
            "mark_stopped keyword-only arguments are invalid. "
            f"Expected {expected_arguments}, received {argument_names}."
        )

    assignments = {
        (
            node.targets[0].attr
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Attribute)
                and isinstance(node.targets[0].value, ast.Name)
                and node.targets[0].value.id == "execution"
            )
            else None
        )
        for node in ast.walk(mark_stopped)
    }

    if "status" not in assignments:
        raise RuntimeError(
            "mark_stopped does not assign execution.status."
        )

    if "completed_at" not in assignments:
        raise RuntimeError(
            "mark_stopped does not assign execution.completed_at."
        )


def transform(source: str) -> str:
    if has_method(source, "mark_stopped"):
        return source

    anchor_count = source.count(INSERTION_ANCHOR)

    if anchor_count != 1:
        raise RuntimeError(
            "Expected exactly one _validate_execution insertion anchor; "
            f"found {anchor_count}."
        )

    return source.replace(
        INSERTION_ANCHOR,
        METHOD_SOURCE + INSERTION_ANCHOR,
        1,
    )


def main() -> int:
    if not TARGET.exists():
        print(f"[ERROR] Target file not found: {TARGET}")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    if has_method(original, "mark_stopped"):
        try:
            validate_source(original)
            py_compile.compile(str(TARGET), doraise=True)
        except Exception as exc:
            print(
                "[ERROR] Existing Commit 4C implementation is invalid: "
                f"{exc}"
            )
            return 1

        print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0004C already applied.")
        print("[OK] AST validation passed.")
        print("[OK] Compilation validation passed.")
        return 0

    backup_path = create_backup(TARGET)

    try:
        transformed = transform(original)

        if transformed == original:
            raise RuntimeError("Patch produced no source changes.")

        validate_source(transformed)

        TARGET.write_text(
            transformed,
            encoding="utf-8",
            newline="",
        )

        py_compile.compile(str(TARGET), doraise=True)
        validate_source(TARGET.read_text(encoding="utf-8"))

    except Exception as exc:
        TARGET.write_text(
            original,
            encoding="utf-8",
            newline="",
        )

        print("[ROLLBACK] Original pipeline_failure_handler.py restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")
        print(f"[ROLLBACK] Backup preserved at: {backup_path}")
        return 1

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0004C applied successfully.")
    print(f"[OK] Modified: {TARGET}")
    print(f"[OK] Backup: {backup_path}")
    print("[OK] PipelineFailureHandler.mark_stopped() created.")
    print("[OK] RuntimePipeline was not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())