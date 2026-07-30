"""
PATCH-RUNTIME-PIPELINE-COMMIT-0005A

Create PipelineCompletionHandler as a standalone runtime component.

This commit creates only pipeline_completion_handler.py. RuntimePipeline is
not modified until the integration commit.
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
    / "pipeline_completion_handler.py"
)

MODULE_SOURCE = '"""\nCompletion handling for RuntimePipeline executions.\n\nThis module determines and applies the terminal state of a pipeline after all\nenabled processors have been evaluated. It intentionally avoids importing\npipeline models to prevent circular dependencies.\n"""\n\nfrom __future__ import annotations\n\nfrom typing import Any, Mapping\n\n\nclass PipelineCompletionHandler:\n    """Determine and apply the terminal state of a pipeline execution."""\n\n    @staticmethod\n    def complete(\n        *,\n        execution: Any,\n        required_by_processor_id: Mapping[str, bool],\n        completed_at: Any,\n        failed_status: Any,\n        warning_status: Any,\n        completed_status: Any,\n    ) -> Any:\n        """\n        Apply the final completion timestamp and status.\n\n        Returns:\n            The terminal status assigned to execution.\n        """\n        PipelineCompletionHandler._validate_execution(execution)\n\n        if not isinstance(required_by_processor_id, Mapping):\n            raise TypeError(\n                "required_by_processor_id must be a mapping."\n            )\n\n        for processor_id, required in required_by_processor_id.items():\n            if not isinstance(processor_id, str):\n                raise TypeError(\n                    "required_by_processor_id keys must be strings."\n                )\n\n            if not isinstance(required, bool):\n                raise TypeError(\n                    "required_by_processor_id values must be bool."\n                )\n\n        if completed_at is None:\n            raise TypeError("completed_at cannot be None.")\n\n        statuses = (\n            failed_status,\n            warning_status,\n            completed_status,\n        )\n\n        if any(status is None for status in statuses):\n            raise TypeError("Completion statuses cannot be None.")\n\n        failed_processor_ids = tuple(\n            execution.failed_processor_ids\n        )\n\n        if failed_processor_ids:\n            missing_ids = tuple(\n                processor_id\n                for processor_id in failed_processor_ids\n                if processor_id not in required_by_processor_id\n            )\n\n            if missing_ids:\n                raise KeyError(\n                    "Missing required-step declarations for failed "\n                    f"processors: {\', \'.join(missing_ids)}."\n                )\n\n            required_failed = any(\n                required_by_processor_id[processor_id]\n                for processor_id in failed_processor_ids\n            )\n\n            terminal_status = (\n                failed_status\n                if required_failed\n                else warning_status\n            )\n        elif execution.warnings:\n            terminal_status = warning_status\n        else:\n            terminal_status = completed_status\n\n        execution.completed_at = completed_at\n        execution.status = terminal_status\n\n        return terminal_status\n\n    @staticmethod\n    def _validate_execution(execution: Any) -> None:\n        if execution is None:\n            raise TypeError("execution cannot be None.")\n\n        required_attributes = (\n            "failed_processor_ids",\n            "warnings",\n            "completed_at",\n            "status",\n        )\n\n        missing_attributes = tuple(\n            attribute\n            for attribute in required_attributes\n            if not hasattr(execution, attribute)\n        )\n\n        if missing_attributes:\n            raise TypeError(\n                "execution is missing required attributes: "\n                f"{\', \'.join(missing_attributes)}."\n            )\n\n\n__all__ = [\n    "PipelineCompletionHandler",\n]\n'


def create_backup(path: Path) -> Path | None:
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(
        f"{path.name}.{timestamp}.bak"
    )
    shutil.copy2(path, backup_path)
    return backup_path


def validate_source(source: str) -> None:
    tree = ast.parse(source, filename=str(TARGET))

    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "PipelineCompletionHandler"
    ]

    if len(classes) != 1:
        raise RuntimeError(
            "Expected exactly one PipelineCompletionHandler class; "
            f"found {len(classes)}."
        )

    method_names = {
        node.name
        for node in classes[0].body
        if isinstance(node, ast.FunctionDef)
    }

    required_methods = {
        "complete",
        "_validate_execution",
    }

    missing = required_methods - method_names
    if missing:
        raise RuntimeError(
            "PipelineCompletionHandler is missing methods: "
            f"{', '.join(sorted(missing))}."
        )


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)

    previous_exists = TARGET.exists()
    original = (
        TARGET.read_text(encoding="utf-8")
        if previous_exists
        else None
    )

    if original == MODULE_SOURCE:
        try:
            validate_source(original)
            py_compile.compile(str(TARGET), doraise=True)
        except Exception as exc:
            print(
                "[ERROR] Existing Commit 5A implementation is invalid: "
                f"{exc}"
            )
            return 1

        print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0005A already applied.")
        print("[OK] AST validation passed.")
        print("[OK] Compilation validation passed.")
        return 0

    backup_path = create_backup(TARGET)

    try:
        validate_source(MODULE_SOURCE)

        TARGET.write_text(
            MODULE_SOURCE,
            encoding="utf-8",
            newline="",
        )

        py_compile.compile(str(TARGET), doraise=True)
        validate_source(TARGET.read_text(encoding="utf-8"))

    except Exception as exc:
        if original is None:
            if TARGET.exists():
                TARGET.unlink()
        else:
            TARGET.write_text(
                original,
                encoding="utf-8",
                newline="",
            )

        print("[ROLLBACK] Original completion-handler state restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")

        if backup_path is not None:
            print(
                "[ROLLBACK] Backup preserved at: "
                f"{backup_path}"
            )

        return 1

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0005A applied successfully.")
    print(f"[OK] Created or updated: {TARGET}")

    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")

    print("[OK] PipelineCompletionHandler created.")
    print("[OK] RuntimePipeline was not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())