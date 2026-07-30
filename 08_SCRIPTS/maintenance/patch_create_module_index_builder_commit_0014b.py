"""
PATCH-CREATE-MODULE-INDEX-BUILDER-COMMIT-0014B

Add the canonical UAAF Patch Engine bootstrap and imports to:

    08_SCRIPTS/maintenance/create_module_index_builder_commit_0014.py

Run:

    python 08_SCRIPTS/maintenance/patch_create_module_index_builder_commit_0014b.py
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

ANCHOR = "# PATCH-0014B-IMPORTS-ANCHOR"

REPLACEMENT = '''SCRIPTS_ROOT = SCRIPT_FILE.parents[1]

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


from uaaf_tools.patch_engine import (  # noqa: E402
    PatchEngine,
    PatchOperation,
    PatchOperationType,
    PatchPlan,
    PatchStatus,
)


PATCH_VERSION = "1.0.0"

# PATCH-0014B-APPLIED
'''


def backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, destination)
    return destination


def main() -> int:
    if not TARGET.is_file():
        print(f"[ERROR] File not found: {TARGET}")
        print("[ERROR] Apply patch 0014A before patch 0014B.")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    if "# PATCH-0014B-APPLIED" in original:
        print("[OK] Patch 0014B already applied.")
        return 0

    occurrences = original.count(ANCHOR)
    if occurrences != 1:
        print(
            "[ERROR] Expected exactly one 0014B import anchor occurrence, "
            f"found {occurrences}."
        )
        return 1

    import_anchor = "import py_compile\n"
    import_occurrences = original.count(import_anchor)
    if import_occurrences != 1:
        print(
            "[ERROR] Expected exactly one py_compile import anchor, "
            f"found {import_occurrences}."
        )
        return 1

    patched = original.replace(
        import_anchor,
        import_anchor + "import sys\n",
        1,
    )
    patched = patched.replace(
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

    print("[OK] PATCH-CREATE-MODULE-INDEX-BUILDER-COMMIT-0014B applied successfully.")
    print(f"[OK] Backup: {backup_file}")
    print("[OK] Canonical Patch Engine imports added.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")
    print("[NEXT] Apply patch 0014C before executing the Commit 0014 generator.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())