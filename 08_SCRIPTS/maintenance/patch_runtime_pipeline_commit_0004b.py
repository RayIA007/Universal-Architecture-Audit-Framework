"""
PATCH-RUNTIME-PIPELINE-COMMIT-0004B

Integrate PipelineFailureHandler into RuntimePipeline.
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

IMPORT_ANCHOR = (
    "from uaaf_core.runtime.pipeline_executor import PipelineExecutor\\n"
)

HANDLER_IMPORT = (
    "from uaaf_core.runtime.pipeline_failure_handler import (\\n"
    "    PipelineFailureHandler,\\n"
    ")\\n"
)

OLD_EXCEPTION_BLOCK = '                except Exception as error:\n                    execution.failed_processor_ids.append(\n                        processor_id\n                    )\n                    execution.executed_processor_ids.append(\n                        processor_id\n                    )\n\n                    message = (\n                        f"Processor {processor_id!r} failed: "\n                        f"{type(error).__name__}: {str(error).strip()}"\n                    )\n                    execution.errors.append(message)\n\n                    if (\n                        step.required\n                        and self.failure_policy\n                        is PipelineFailurePolicy.STOP_ON_ERROR\n                    ):\n'
NEW_EXCEPTION_BLOCK = '                except Exception as error:\n                    decision = PipelineFailureHandler.handle(\n                        processor_id=processor_id,\n                        error=error,\n                        required=step.required,\n                        stop_on_error=(\n                            self.failure_policy\n                            is PipelineFailurePolicy.STOP_ON_ERROR\n                        ),\n                        execution=execution,\n                    )\n\n                    if decision.should_stop:\n'


def create_backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def validate_ast(source: str) -> None:
    tree = ast.parse(source, filename=str(TARGET))

    runtime_pipeline_found = any(
        isinstance(node, ast.ClassDef)
        and node.name == "RuntimePipeline"
        for node in ast.walk(tree)
    )

    handler_import_found = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "uaaf_core.runtime.pipeline_failure_handler"
        and any(
            alias.name == "PipelineFailureHandler"
            for alias in node.names
        )
        for node in ast.walk(tree)
    )

    handler_call_found = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "handle"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "PipelineFailureHandler"
        for node in ast.walk(tree)
    )

    decision_condition_found = any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Attribute)
        and node.test.attr == "should_stop"
        and isinstance(node.test.value, ast.Name)
        and node.test.value.id == "decision"
        for node in ast.walk(tree)
    )

    if not runtime_pipeline_found:
        raise RuntimeError("RuntimePipeline class was not found.")

    if not handler_import_found:
        raise RuntimeError(
            "PipelineFailureHandler import was not found."
        )

    if not handler_call_found:
        raise RuntimeError(
            "PipelineFailureHandler.handle() call was not found."
        )

    if not decision_condition_found:
        raise RuntimeError(
            "decision.should_stop condition was not found."
        )


def is_already_applied(source: str) -> bool:
    return (
        HANDLER_IMPORT in source
        and "decision = PipelineFailureHandler.handle(" in source
        and "if decision.should_stop:" in source
        and OLD_EXCEPTION_BLOCK not in source
    )


def transform(source: str) -> str:
    transformed = source

    if HANDLER_IMPORT not in transformed:
        anchor_count = transformed.count(IMPORT_ANCHOR)

        if anchor_count != 1:
            raise RuntimeError(
                "Expected exactly one PipelineExecutor import anchor; "
                f"found {anchor_count}."
            )

        transformed = transformed.replace(
            IMPORT_ANCHOR,
            IMPORT_ANCHOR + HANDLER_IMPORT,
            1,
        )

    if OLD_EXCEPTION_BLOCK in transformed:
        block_count = transformed.count(OLD_EXCEPTION_BLOCK)

        if block_count != 1:
            raise RuntimeError(
                "Expected exactly one legacy exception block; "
                f"found {block_count}."
            )

        transformed = transformed.replace(
            OLD_EXCEPTION_BLOCK,
            NEW_EXCEPTION_BLOCK,
            1,
        )
    elif not (
        "decision = PipelineFailureHandler.handle(" in transformed
        and "if decision.should_stop:" in transformed
    ):
        raise RuntimeError(
            "Legacy exception block was not found and "
            "the new integration is not present."
        )

    return transformed


def main() -> int:
    if not TARGET.exists():
        print(f"[ERROR] Target file not found: {TARGET}")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    if is_already_applied(original):
        try:
            validate_ast(original)
            py_compile.compile(str(TARGET), doraise=True)
        except Exception as exc:
            print(
                "[ERROR] Existing Commit 4B integration is invalid: "
                f"{exc}"
            )
            return 1

        print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0004B already applied.")
        print("[OK] AST validation passed.")
        print("[OK] Compilation validation passed.")
        return 0

    backup_path = create_backup(TARGET)

    try:
        transformed = transform(original)

        if transformed == original:
            raise RuntimeError("Patch produced no source changes.")

        validate_ast(transformed)

        TARGET.write_text(
            transformed,
            encoding="utf-8",
            newline="",
        )

        py_compile.compile(str(TARGET), doraise=True)

        written = TARGET.read_text(encoding="utf-8")
        validate_ast(written)

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

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0004B applied successfully.")
    print(f"[OK] Modified: {TARGET}")
    print(f"[OK] Backup: {backup_path}")
    print("[OK] PipelineFailureHandler import integrated.")
    print("[OK] Failure recording delegated to PipelineFailureHandler.")
    print("[OK] decision.should_stop integrated.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())