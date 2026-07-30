"""
PATCH-RUNTIME-PIPELINE-COMMIT-0002C

Remove obsolete RuntimePipeline._capture_failed_result() after delegating
processor execution and failure-result capture to PipelineExecutor.

Run:

    python 08_SCRIPTS/maintenance/patch_runtime_pipeline_commit_0002c.py
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

START_MARKER = (
    "    @staticmethod\n"
    "    def _capture_failed_result(\n"
)

END_MARKER = (
    "    @staticmethod\n"
    "    def _dependency_failed(\n"
)


def create_backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def main() -> int:
    if not TARGET.exists():
        print(f"[ERROR] Target file not found: {TARGET}")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    start_count = original.count(START_MARKER)
    end_count = original.count(END_MARKER)

    if start_count == 0:
        if end_count == 1:
            print("[OK] Patch already applied.")
            return 0

        print(
            "[ERROR] _capture_failed_result() was not found and the expected "
            "_dependency_failed() boundary is invalid."
        )
        return 1

    if start_count != 1:
        print(
            "[ERROR] Expected exactly one _capture_failed_result() definition, "
            f"found {start_count}."
        )
        return 1

    if end_count != 1:
        print(
            "[ERROR] Expected exactly one _dependency_failed() boundary, "
            f"found {end_count}."
        )
        return 1

    start_index = original.find(START_MARKER)
    end_index = original.find(END_MARKER, start_index)

    if end_index == -1 or end_index <= start_index:
        print(
            "[ERROR] Unable to determine "
            "_capture_failed_result() method boundaries."
        )
        return 1

    patched = original[:start_index] + original[end_index:]

    try:
        ast.parse(patched, filename=str(TARGET))
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

    except Exception as exc:
        TARGET.write_text(
            original,
            encoding="utf-8",
            newline="",
        )

        print(f"[ROLLBACK] Patch failed: {exc}")
        print("[ROLLBACK] Original source restored.")
        print(f"[ROLLBACK] Backup preserved at: {backup_path}")
        return 1

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0002C applied successfully.")
    print(f"[OK] Backup: {backup_path}")
    print("[OK] Legacy RuntimePipeline._capture_failed_result() removed.")
    print("[OK] _dependency_failed() preserved.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())