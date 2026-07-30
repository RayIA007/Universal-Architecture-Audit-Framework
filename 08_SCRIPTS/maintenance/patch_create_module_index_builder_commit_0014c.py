"""
PATCH-CREATE-MODULE-INDEX-BUILDER-COMMIT-0014C

Add Commit 0014 identifiers, target metadata, and source-section anchors to:

    08_SCRIPTS/maintenance/create_module_index_builder_commit_0014.py

Run:

    python 08_SCRIPTS/maintenance/patch_create_module_index_builder_commit_0014c.py
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
    / "maintenance"
    / "create_module_index_builder_commit_0014.py"
)

ANCHOR = "# PATCH-0014C-CONTENT-ANCHOR"

REPLACEMENT = '''PATCH_ID = "uaaf-commit-0014-architecture-module-index"
PATCH_NAME = "Add Architecture Auditor module index"
TARGET_FILE = TARGET


# PATCH-0014D-OLD-SOURCE-ANCHOR


# PATCH-0014E-NEW-SOURCE-PART-1-ANCHOR


# PATCH-0014F-NEW-SOURCE-PART-2-ANCHOR


# PATCH-0014G-PATCH-PLAN-ANCHOR


# PATCH-0014C-APPLIED
'''


def backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, destination)
    return destination


def main() -> int:
    if not TARGET.is_file():
        print(f"[ERROR] File not found: {TARGET}")
        print("[ERROR] Apply patches 0014A and 0014B before patch 0014C.")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    if "# PATCH-0014C-APPLIED" in original:
        print("[OK] Patch 0014C already applied.")
        return 0

    if "# PATCH-0014B-APPLIED" not in original:
        print("[ERROR] Patch 0014B has not been applied.")
        return 1

    occurrences = original.count(ANCHOR)
    if occurrences != 1:
        print(
            "[ERROR] Expected exactly one 0014C content anchor occurrence, "
            f"found {occurrences}."
        )
        return 1

    patched = original.replace(
        ANCHOR,
        REPLACEMENT,
        1,
    )

    try:
        ast.parse(patched)
    except SyntaxError as exc:
        print(f"[ERROR] Patched source failed AST validation: {exc}")
        return 1

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

    print("[OK] PATCH-CREATE-MODULE-INDEX-BUILDER-COMMIT-0014C applied successfully.")
    print(f"[OK] Backup: {backup_file}")
    print("[OK] Commit identifiers and target metadata added.")
    print("[OK] Incremental source and PatchPlan anchors added.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")
    print("[NEXT] Apply patch 0014D before executing the Commit 0014 generator.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())