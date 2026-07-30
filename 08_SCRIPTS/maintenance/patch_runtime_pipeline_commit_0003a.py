"""
PATCH-RUNTIME-PIPELINE-COMMIT-0003A

Create the PipelineDependencyGuard module without modifying RuntimePipeline.
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
    / "pipeline_dependency_guard.py"
)

MODULE_SOURCE = '"""\nPipeline dependency guard for the Universal Architecture Audit Framework.\n\nResponsible only for deciding whether a processor must be skipped because\none of its declared dependencies failed or was skipped.\n"""\n\nfrom __future__ import annotations\n\nfrom collections.abc import Iterable\n\n\nclass PipelineDependencyGuard:\n    """Evaluate whether processor dependencies prevent execution."""\n\n    @staticmethod\n    def should_skip(\n        *,\n        dependencies: Iterable[str],\n        failed_processor_ids: Iterable[str],\n        skipped_processor_ids: Iterable[str],\n    ) -> bool:\n        """\n        Return whether any dependency failed or was previously skipped.\n\n        The guard is intentionally independent from RuntimePipeline models so\n        it can be reused without introducing circular imports.\n        """\n        failed = set(failed_processor_ids)\n        skipped = set(skipped_processor_ids)\n\n        return any(\n            dependency in failed or dependency in skipped\n            for dependency in dependencies\n        )\n\n\n__all__ = [\n    "PipelineDependencyGuard",\n]\n'


def create_backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)

    try:
        ast.parse(MODULE_SOURCE, filename=str(TARGET))
    except SyntaxError as exc:
        print(f"[ERROR] Module source failed AST validation: {exc}")
        return 1

    if TARGET.exists():
        current = TARGET.read_text(encoding="utf-8")

        if current == MODULE_SOURCE:
            print("[OK] Patch already applied.")
            return 0

        backup_path = create_backup(TARGET)
        original = current
    else:
        backup_path = None
        original = None

    try:
        TARGET.write_text(MODULE_SOURCE, encoding="utf-8", newline="")
        py_compile.compile(str(TARGET), doraise=True)
    except Exception as exc:
        if original is None:
            TARGET.unlink(missing_ok=True)
            print("[ROLLBACK] Newly created file removed.")
        else:
            TARGET.write_text(original, encoding="utf-8", newline="")
            print("[ROLLBACK] Original file restored.")

        print(f"[ROLLBACK] Patch failed: {exc}")

        if backup_path is not None:
            print(f"[ROLLBACK] Backup preserved at: {backup_path}")

        return 1

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0003A applied successfully.")
    print(f"[OK] Created: {TARGET}")

    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")

    print("[OK] PipelineDependencyGuard created.")
    print("[OK] RuntimePipeline was not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())