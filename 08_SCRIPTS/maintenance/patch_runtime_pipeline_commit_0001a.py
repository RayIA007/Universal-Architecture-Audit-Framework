"""
PATCH-RUNTIME-PIPELINE-COMMIT-0001A

Integrate DependencyResolver into RuntimePipeline validation while preserving
the existing internal topological-sort implementation for subsequent cleanup.

Run:

    python 08_SCRIPTS/maintenance/patch_runtime_pipeline_commit_0001a.py
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

IMPORT_ANCHOR = (
    "from uaaf_core.contracts.processor import ProcessorResult\n"
    "from uaaf_core.runtime.runtime_context import RuntimeContext\n"
)

IMPORT_REPLACEMENT = (
    "from uaaf_core.contracts.processor import ProcessorResult\n"
    "from uaaf_core.runtime.dependency_resolver import DependencyResolver\n"
    "from uaaf_core.runtime.runtime_context import RuntimeContext\n"
)

OLD_CALL = "return self._stable_topological_order(enabled_steps)"
NEW_CALL = "return DependencyResolver.resolve(enabled_steps)"


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

    import_applied = (
        "from uaaf_core.runtime.dependency_resolver "
        "import DependencyResolver"
    ) in original
    call_applied = NEW_CALL in original

    if import_applied and call_applied:
        print("[OK] Patch already applied.")
        return 0

    if import_applied != call_applied:
        print(
            "[ERROR] Partial patch state detected. "
            "Restore the previous backup before retrying."
        )
        return 1

    import_occurrences = original.count(IMPORT_ANCHOR)
    call_occurrences = original.count(OLD_CALL)

    if import_occurrences != 1:
        print(
            "[ERROR] Expected exactly one import anchor occurrence, "
            f"found {import_occurrences}."
        )
        return 1

    if call_occurrences != 1:
        print(
            "[ERROR] Expected exactly one dependency-resolution call, "
            f"found {call_occurrences}."
        )
        return 1

    patched = original.replace(
        IMPORT_ANCHOR,
        IMPORT_REPLACEMENT,
        1,
    )
    patched = patched.replace(
        OLD_CALL,
        NEW_CALL,
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

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0001A applied successfully.")
    print(f"[OK] Backup: {backup_file}")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())