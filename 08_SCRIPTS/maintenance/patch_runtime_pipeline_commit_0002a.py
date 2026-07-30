"""
PATCH-RUNTIME-PIPELINE-COMMIT-0002A

Integrate PipelineExecutor into RuntimePipeline without removing the legacy
execution helpers yet.

Changes:
1. Add the PipelineExecutor import.
2. Delegate processor execution to PipelineExecutor.execute_processor().

Run:

    python 08_SCRIPTS/maintenance/patch_runtime_pipeline_commit_0002a.py
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

EXECUTOR_FILE = (
    PROJECT_ROOT
    / "08_SCRIPTS"
    / "uaaf_core"
    / "runtime"
    / "pipeline_executor.py"
)

EXECUTOR_IMPORT = (
    "from uaaf_core.runtime.pipeline_executor import PipelineExecutor\n"
)

IMPORT_ANCHOR = (
    "from uaaf_core.runtime.dependency_resolver import DependencyResolver\n"
)

OLD_CALL = """                    result = self._execute_step(
                        context=context,
                        processor_id=processor_id,
                    )
"""

NEW_CALL = """                    result = PipelineExecutor.execute_processor(
                        context=context,
                        processor_id=processor_id,
                    )
"""


def create_backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def validate_python(source: str, filename: str) -> None:
    ast.parse(source, filename=filename)


def main() -> int:
    if not TARGET.exists():
        print(f"[ERROR] Target file not found: {TARGET}")
        return 1

    if not EXECUTOR_FILE.exists():
        print(f"[ERROR] PipelineExecutor file not found: {EXECUTOR_FILE}")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    import_present = EXECUTOR_IMPORT in original
    old_call_count = original.count(OLD_CALL)
    new_call_count = original.count(NEW_CALL)

    if import_present and old_call_count == 0 and new_call_count == 1:
        print("[OK] Patch already applied.")
        return 0

    if old_call_count != 1:
        print(
            "[ERROR] Expected exactly one RuntimePipeline._execute_step call, "
            f"found {old_call_count}."
        )
        return 1

    patched = original

    if not import_present:
        anchor_count = patched.count(IMPORT_ANCHOR)

        if anchor_count != 1:
            print(
                "[ERROR] Expected exactly one DependencyResolver import "
                f"anchor, found {anchor_count}."
            )
            return 1

        patched = patched.replace(
            IMPORT_ANCHOR,
            IMPORT_ANCHOR + EXECUTOR_IMPORT,
            1,
        )

    patched = patched.replace(
        OLD_CALL,
        NEW_CALL,
        1,
    )

    try:
        validate_python(patched, str(TARGET))
    except SyntaxError as exc:
        print(f"[ERROR] Patched source failed AST validation: {exc}")
        return 1

    backup_path = create_backup(TARGET)

    try:
        TARGET.write_text(
            patched,
            encoding="utf-8",
            newline="",
        )

        py_compile.compile(
            str(TARGET),
            doraise=True,
        )

        py_compile.compile(
            str(EXECUTOR_FILE),
            doraise=True,
        )

    except Exception as exc:
        TARGET.write_text(
            original,
            encoding="utf-8",
            newline="",
        )

        print(f"[ROLLBACK] Patch failed: {exc}")
        print(f"[ROLLBACK] Original restored from memory.")
        print(f"[ROLLBACK] Backup preserved at: {backup_path}")
        return 1

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0002A applied successfully.")
    print(f"[OK] Backup: {backup_path}")
    print("[OK] PipelineExecutor import added.")
    print("[OK] Processor execution delegated to PipelineExecutor.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")
    print("[INFO] Legacy _execute_step() and _capture_failed_result() remain")
    print("[INFO] temporarily and will be removed in commits 2B and 2C.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())