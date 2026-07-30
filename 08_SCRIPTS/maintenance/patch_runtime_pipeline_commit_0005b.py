"""
PATCH-RUNTIME-PIPELINE-COMMIT-0005B

Integrate PipelineCompletionHandler into RuntimePipeline.

This commit replaces only the final execution-status decision block. Context
finalization and returning the execution remain owned by RuntimePipeline.
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

OLD_IMPORT_ANCHOR = 'from uaaf_core.runtime.pipeline_dependency_guard import PipelineDependencyGuard\n'
NEW_IMPORT_BLOCK = 'from uaaf_core.runtime.pipeline_completion_handler import (\n    PipelineCompletionHandler,\n)\nfrom uaaf_core.runtime.pipeline_dependency_guard import PipelineDependencyGuard\n'
OLD_COMPLETION_BLOCK = '            execution.completed_at = datetime.now(UTC)\n\n            if execution.failed_processor_ids:\n                required_failed = any(\n                    step_map[processor_id].required\n                    for processor_id\n                    in execution.failed_processor_ids\n                )\n                execution.status = (\n                    PipelineStatus.FAILED\n                    if required_failed\n                    else PipelineStatus.COMPLETED_WITH_WARNINGS\n                )\n            elif execution.has_warnings:\n                execution.status = (\n                    PipelineStatus.COMPLETED_WITH_WARNINGS\n                )\n            else:\n                execution.status = PipelineStatus.COMPLETED\n\n'
NEW_COMPLETION_BLOCK = '            PipelineCompletionHandler.complete(\n                execution=execution,\n                required_by_processor_id={\n                    processor_id: step.required\n                    for processor_id, step in step_map.items()\n                },\n                completed_at=datetime.now(UTC),\n                failed_status=PipelineStatus.FAILED,\n                warning_status=(\n                    PipelineStatus.COMPLETED_WITH_WARNINGS\n                ),\n                completed_status=PipelineStatus.COMPLETED,\n            )\n\n'


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

    completion_imports = [
        node
        for node in tree.body
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            == "uaaf_core.runtime.pipeline_completion_handler"
            and any(
                alias.name == "PipelineCompletionHandler"
                for alias in node.names
            )
        )
    ]

    if len(completion_imports) != 1:
        raise RuntimeError(
            "Expected exactly one PipelineCompletionHandler import; "
            f"found {len(completion_imports)}."
        )

    completion_calls = [
        node
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "complete"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "PipelineCompletionHandler"
        )
    ]

    if len(completion_calls) != 1:
        raise RuntimeError(
            "Expected exactly one "
            "PipelineCompletionHandler.complete() call; "
            f"found {len(completion_calls)}."
        )

    keyword_names = {
        keyword.arg
        for keyword in completion_calls[0].keywords
    }

    expected_keywords = {
        "execution",
        "required_by_processor_id",
        "completed_at",
        "failed_status",
        "warning_status",
        "completed_status",
    }

    if keyword_names != expected_keywords:
        raise RuntimeError(
            "PipelineCompletionHandler.complete() arguments are invalid. "
            f"Expected {sorted(expected_keywords)}, "
            f"received {sorted(keyword_names)}."
        )

    if OLD_COMPLETION_BLOCK in source:
        raise RuntimeError(
            "Legacy completion-status block is still present."
        )

    if source.count("self._finalize_context(") < 2:
        raise RuntimeError(
            "RuntimePipeline context finalization was not preserved."
        )

    if "return execution" not in source:
        raise RuntimeError(
            "RuntimePipeline execution return was not preserved."
        )


def is_already_applied(source: str) -> bool:
    return (
        "PipelineCompletionHandler.complete(" in source
        and OLD_COMPLETION_BLOCK not in source
    )


def transform(source: str) -> str:
    transformed = source

    import_present = (
        "from uaaf_core.runtime.pipeline_completion_handler import ("
        in transformed
    )

    if not import_present:
        import_anchor_count = transformed.count(
            OLD_IMPORT_ANCHOR
        )

        if import_anchor_count != 1:
            raise RuntimeError(
                "Expected exactly one dependency-guard import anchor; "
                f"found {import_anchor_count}."
            )

        transformed = transformed.replace(
            OLD_IMPORT_ANCHOR,
            NEW_IMPORT_BLOCK,
            1,
        )

    if "PipelineCompletionHandler.complete(" not in transformed:
        completion_count = transformed.count(
            OLD_COMPLETION_BLOCK
        )

        if completion_count != 1:
            raise RuntimeError(
                "Expected exactly one final completion block; "
                f"found {completion_count}."
            )

        transformed = transformed.replace(
            OLD_COMPLETION_BLOCK,
            NEW_COMPLETION_BLOCK,
            1,
        )

    return transformed


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
                "[ERROR] Existing Commit 5B integration is invalid: "
                f"{exc}"
            )
            return 1

        print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0005B already applied.")
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

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0005B applied successfully.")
    print(f"[OK] Modified: {TARGET}")
    print(f"[OK] Backup: {backup_path}")
    print("[OK] Final execution status delegated to PipelineCompletionHandler.")
    print("[OK] Context finalization remains in RuntimePipeline.")
    print("[OK] Execution return remains unchanged.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())