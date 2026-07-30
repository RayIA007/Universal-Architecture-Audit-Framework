"""
PATCH-RUNTIME-PIPELINE-COMMIT-0001C

Remove obsolete collections imports after DependencyResolver extraction.

Run:

    python 08_SCRIPTS/maintenance/patch_runtime_pipeline_commit_0001c.py
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

OLD_IMPORT = "from collections import defaultdict, deque\n"


def backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, destination)
    return destination


def main() -> int:
    if not TARGET.exists():
        print(f"[ERROR] File not found: {TARGET}")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    if OLD_IMPORT not in original:
        print("[OK] Patch already applied.")
        return 0

    occurrences = original.count(OLD_IMPORT)

    if occurrences != 1:
        print(
            "[ERROR] Expected exactly one obsolete collections import, "
            f"found {occurrences}."
        )
        return 1

    patched = original.replace(
        OLD_IMPORT,
        "",
        1,
    )

    ast.parse(patched)

    backup_file = backup(TARGET)

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

        print(f"[ROLLBACK] {exc}")
        print(f"[ROLLBACK] Backup: {backup_file}")
        return 1

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0001C applied successfully.")
    print(f"[OK] Backup: {backup_file}")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())