"""
PATCH-RUNTIME-PIPELINE-COMMIT-0004D

Integrate PipelineFailureHandler.mark_stopped() into RuntimePipeline.

This commit replaces only the terminal status and completion timestamp
assignments inside the stop-on-error branch. Context finalization and exception
propagation remain owned by RuntimePipeline.
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
    / "pipeline.py"
)

OLD_BLOCK = '                    if decision.should_stop:\n                        execution.status = PipelineStatus.FAILED\n                        execution.completed_at = datetime.now(UTC)\n                        self._finalize_context(\n                            context=context,\n                            execution=execution,\n                        )\n                        raise\n'
NEW_BLOCK = '                    if decision.should_stop:\n                        PipelineFailureHandler.mark_stopped(\n                            execution=execution,\n                            failed_status=PipelineStatus.FAILED,\n                            completed_at=datetime.now(UTC),\n                        )\n                        self._finalize_context(\n                            context=context,\n                            execution=execution,\n                        )\n                        raise\n'


def create_backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(
        f"{path.name}.{timestamp}.bak"
    )
    shutil.copy2(path, backup_path)
    return backup_path


def parse_module(source: str) -> ast.Module:
    return ast.parse(source, filename=str(TARGET))


def validate_source(source: str) -> None:
    tree = parse_module(source)

    handler_import_found = any(
        isinstance(node, ast.ImportFrom)
        and node.module
        == "uaaf_core.runtime.pipeline_failure_handler"
        and any(
            alias.name == "PipelineFailureHandler"
            for alias in node.names
        )
        for node in ast.walk(tree)
    )

    mark_stopped_calls = [
        node
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "mark_stopped"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "PipelineFailureHandler"
        )
    ]

    if not handler_import_found:
        raise RuntimeError(
            "PipelineFailureHandler import was not found."
        )

    if len(mark_stopped_calls) != 1:
        raise RuntimeError(
            "Expected exactly one "
            "PipelineFailureHandler.mark_stopped() call; "
            f"found {len(mark_stopped_calls)}."
        )

    keyword_names = {
        keyword.arg
        for keyword in mark_stopped_calls[0].keywords
    }

    expected_keywords = {
        "execution",
        "failed_status",
        "completed_at",
    }

    if keyword_names != expected_keywords:
        raise RuntimeError(
            "mark_stopped() keyword arguments are invalid. "
            f"Expected {sorted(expected_keywords)}, "
            f"received {sorted(keyword_names)}."
        )

    if OLD_BLOCK in source:
        raise RuntimeError(
            "Legacy terminal failure block is still present."
        )

    if "if decision.should_stop:" not in source:
        raise RuntimeError(
            "decision.should_stop branch was not found."
        )

    if "self._finalize_context(" not in source:
        raise RuntimeError(
            "RuntimePipeline context finalization was not preserved."
        )


def is_already_applied(source: str) -> bool:
    return (
        "PipelineFailureHandler.mark_stopped(" in source
        and OLD_BLOCK not in source
    )


def transform(source: str) -> str:
    if is_already_applied(source):
        return source

    block_count = source.count(OLD_BLOCK)

    if block_count != 1:
        raise RuntimeError(
            "Expected exactly one terminal failure block; "
            f"found {block_count}."
        )

    return source.replace(
        OLD_BLOCK,
        NEW_BLOCK,
        1,
    )


def main() -> int:
    if not TARGET.exists():
        print(f"[ERROR] Target file not found: {TARGET}")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    if is_already_applied(original):
        try:
            validate_source(original)
            py_compile.compile(str(TARGET), doraise=True)
        except Exception as exc:
            print(
                "[ERROR] Existing Commit 4D integration is invalid: "
                f"{exc}"
            )
            return 1

        print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0004D already applied.")
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

        print("[ROLLBACK] Original pipeline.py restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")
        print(f"[ROLLBACK] Backup preserved at: {backup_path}")
        return 1

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0004D applied successfully.")
    print(f"[OK] Modified: {TARGET}")
    print(f"[OK] Backup: {backup_path}")
    print("[OK] Terminal failure state delegated to PipelineFailureHandler.")
    print("[OK] Context finalization remains in RuntimePipeline.")
    print("[OK] Exception propagation remains unchanged.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())