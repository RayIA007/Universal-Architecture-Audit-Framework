"""
PATCH-RUNTIME-PIPELINE-COMMIT-0002D

Remove the obsolete ProcessorResult import from RuntimePipeline after
execution and failed-result capture were delegated to PipelineExecutor.

Run:

    python 08_SCRIPTS/maintenance/patch_runtime_pipeline_commit_0002d.py
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

OBSOLETE_IMPORT = (
    "from uaaf_core.contracts.processor import ProcessorResult\n"
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
    import_count = original.count(OBSOLETE_IMPORT)

    if import_count == 0:
        print("[OK] Patch already applied.")
        return 0

    if import_count != 1:
        print(
            "[ERROR] Expected exactly one obsolete ProcessorResult import, "
            f"found {import_count}."
        )
        return 1

    patched = original.replace(
        OBSOLETE_IMPORT,
        "",
        1,
    )

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

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0002D applied successfully.")
    print(f"[OK] Backup: {backup_path}")
    print("[OK] Obsolete ProcessorResult import removed.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())