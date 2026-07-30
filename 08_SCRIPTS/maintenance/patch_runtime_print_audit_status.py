"""
PATCH-0002

Replace obsolete runtime.audit.status access with the RuntimeContext-backed
Audit reference exposed through runtime.session.audit.

Run:

    python 08_SCRIPTS/maintenance/patch_runtime_print_audit_status.py
"""

from __future__ import annotations

import ast
import py_compile
import shutil
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_FILE = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_FILE.parents[2]

TARGET = (
    PROJECT_ROOT
    / "08_SCRIPTS"
    / "tests"
    / "runtime_pipeline_integration_test.py"
)

OLD = "print(runtime.audit.status.value)"
NEW = "print(runtime.session.audit.status.value)"


def backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, dst)
    return dst


def main() -> int:

    if not TARGET.exists():
        print(f"[ERROR] File not found: {TARGET}")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    if NEW in original:
        print("[OK] Patch already applied.")
        return 0

    occurrences = original.count(OLD)

    if occurrences != 1:
        print(
            f"[ERROR] Expected exactly one occurrence, found {occurrences}."
        )
        return 1

    patched = original.replace(OLD, NEW)

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

    print("[OK] PATCH-0002 applied successfully.")
    print(f"[OK] Backup: {backup_file}")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())