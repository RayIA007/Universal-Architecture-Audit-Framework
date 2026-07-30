"""
PATCH-RUNTIME-PIPELINE-COMMIT-0004A

Create PipelineFailureHandler without modifying RuntimePipeline.

Run:

    python 08_SCRIPTS/maintenance/patch_runtime_pipeline_commit_0004a.py
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

MODULE_SOURCE = '"""\nPipeline failure handler for the Universal Architecture Audit Framework.\n\nThis module centralizes processor-exception recording and the decision to stop\nor continue pipeline execution. It deliberately avoids importing pipeline\nmodels so RuntimePipeline can integrate it without circular dependencies.\n"""\n\nfrom __future__ import annotations\n\nfrom dataclasses import dataclass\nfrom typing import Any\n\n\n@dataclass(frozen=True, slots=True)\nclass PipelineFailureDecision:\n    """Immutable result of evaluating one processor failure."""\n\n    message: str\n    should_stop: bool\n\n\nclass PipelineFailureHandler:\n    """Record processor failures and evaluate the configured stop policy."""\n\n    @staticmethod\n    def handle(\n        *,\n        processor_id: str,\n        error: Exception,\n        required: bool,\n        stop_on_error: bool,\n        execution: Any,\n    ) -> PipelineFailureDecision:\n        """\n        Record a processor exception and return the resulting control decision.\n\n        The execution object must expose the mutable attributes\n        ``failed_processor_ids``, ``executed_processor_ids``, and ``errors``.\n        """\n        if not isinstance(processor_id, str):\n            raise TypeError("processor_id must be a string.")\n\n        normalized_processor_id = processor_id.strip()\n        if not normalized_processor_id:\n            raise ValueError("processor_id cannot be empty.")\n\n        if not isinstance(error, Exception):\n            raise TypeError("error must be an Exception instance.")\n\n        if not isinstance(required, bool):\n            raise TypeError("required must be a bool.")\n\n        if not isinstance(stop_on_error, bool):\n            raise TypeError("stop_on_error must be a bool.")\n\n        PipelineFailureHandler._validate_execution(execution)\n\n        message = (\n            f"Processor {normalized_processor_id!r} failed: "\n            f"{type(error).__name__}: {str(error).strip()}"\n        )\n\n        execution.failed_processor_ids.append(normalized_processor_id)\n        execution.executed_processor_ids.append(normalized_processor_id)\n        execution.errors.append(message)\n\n        return PipelineFailureDecision(\n            message=message,\n            should_stop=required and stop_on_error,\n        )\n\n    @staticmethod\n    def _validate_execution(execution: Any) -> None:\n        required_attributes = (\n            "failed_processor_ids",\n            "executed_processor_ids",\n            "errors",\n        )\n\n        missing = tuple(\n            attribute\n            for attribute in required_attributes\n            if not hasattr(execution, attribute)\n        )\n\n        if missing:\n            raise TypeError(\n                "execution is missing required attributes: "\n                f"{\', \'.join(missing)}."\n            )\n\n        invalid = tuple(\n            attribute\n            for attribute in required_attributes\n            if not isinstance(getattr(execution, attribute), list)\n        )\n\n        if invalid:\n            raise TypeError(\n                "execution attributes must be lists: "\n                f"{\', \'.join(invalid)}."\n            )\n\n\n__all__ = [\n    "PipelineFailureDecision",\n    "PipelineFailureHandler",\n]\n'


def create_backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def validate_module_source(source: str) -> None:
    tree = ast.parse(source, filename=str(TARGET))

    class_names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }

    expected = {
        "PipelineFailureDecision",
        "PipelineFailureHandler",
    }

    missing = expected - class_names
    if missing:
        raise RuntimeError(
            "Generated module is missing classes: "
            f"{', '.join(sorted(missing))}."
        )


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)

    try:
        validate_module_source(MODULE_SOURCE)
    except Exception as exc:
        print(f"[ERROR] Module source validation failed: {exc}")
        return 1

    if TARGET.exists():
        original = TARGET.read_text(encoding="utf-8")

        if original == MODULE_SOURCE:
            print("[OK] Patch already applied.")
            return 0

        backup_path = create_backup(TARGET)
    else:
        original = None
        backup_path = None

    try:
        TARGET.write_text(
            MODULE_SOURCE,
            encoding="utf-8",
            newline="",
        )

        py_compile.compile(
            str(TARGET),
            doraise=True,
        )

        written = TARGET.read_text(encoding="utf-8")
        validate_module_source(written)

    except Exception as exc:
        if original is None:
            TARGET.unlink(missing_ok=True)
            print("[ROLLBACK] Newly created file removed.")
        else:
            TARGET.write_text(
                original,
                encoding="utf-8",
                newline="",
            )
            print("[ROLLBACK] Original file restored.")

        print(f"[ROLLBACK] Patch failed: {exc}")

        if backup_path is not None:
            print(f"[ROLLBACK] Backup preserved at: {backup_path}")

        return 1

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0004A applied successfully.")
    print(f"[OK] Created: {TARGET}")

    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")

    print("[OK] PipelineFailureDecision created.")
    print("[OK] PipelineFailureHandler created.")
    print("[OK] RuntimePipeline was not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())