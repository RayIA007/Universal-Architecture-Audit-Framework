"""
PATCH-RUNTIME-PIPELINE-COMMIT-0003B

Integrate PipelineDependencyGuard into RuntimePipeline without removing
RuntimePipeline._dependency_failed() yet.

Run:

    python 08_SCRIPTS/maintenance/patch_runtime_pipeline_commit_0003b.py
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
    "from uaaf_core.runtime.dependency_resolver import DependencyResolver\n"
    "from uaaf_core.runtime.pipeline_executor import PipelineExecutor\n"
)

IMPORT_REPLACEMENT = (
    "from uaaf_core.runtime.dependency_resolver import DependencyResolver\n"
    "from uaaf_core.runtime.pipeline_dependency_guard import "
    "PipelineDependencyGuard\n"
    "from uaaf_core.runtime.pipeline_executor import PipelineExecutor\n"
)

CALL_ANCHOR = """                if self._dependency_failed(
                    step=step,
                    execution=execution,
                ):
"""

CALL_REPLACEMENT = """                if PipelineDependencyGuard.should_skip(
                    dependencies=step.depends_on,
                    failed_processor_ids=execution.failed_processor_ids,
                    skipped_processor_ids=execution.skipped_processor_ids,
                ):
"""


def create_backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def validate_source(source: str, filename: Path) -> None:
    ast.parse(source, filename=str(filename))


def main() -> int:
    if not TARGET.exists():
        print(f"[ERROR] Target file not found: {TARGET}")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    import_present = (
        "from uaaf_core.runtime.pipeline_dependency_guard import "
        "PipelineDependencyGuard\n"
        in original
    )
    call_present = "if PipelineDependencyGuard.should_skip(" in original

    if import_present and call_present:
        print("[OK] Patch already applied.")
        return 0

    updated = original

    if not import_present:
        if IMPORT_ANCHOR not in updated:
            print("[ERROR] Import anchor not found. No changes were made.")
            return 1
        updated = updated.replace(
            IMPORT_ANCHOR,
            IMPORT_REPLACEMENT,
            1,
        )

    if not call_present:
        if CALL_ANCHOR not in updated:
            print("[ERROR] Dependency call anchor not found. No changes were made.")
            return 1
        updated = updated.replace(
            CALL_ANCHOR,
            CALL_REPLACEMENT,
            1,
        )

    if updated == original:
        print("[OK] No changes required.")
        return 0

    try:
        validate_source(updated, TARGET)
    except SyntaxError as exc:
        print(f"[ERROR] Updated source failed AST validation: {exc}")
        return 1

    backup_path = create_backup(TARGET)

    try:
        TARGET.write_text(
            updated,
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

        print("[ROLLBACK] Original pipeline.py restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")
        print(f"[ROLLBACK] Backup preserved at: {backup_path}")
        return 1

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0003B applied successfully.")
    print(f"[OK] Updated: {TARGET}")
    print(f"[OK] Backup: {backup_path}")
    print("[OK] PipelineDependencyGuard imported.")
    print("[OK] RuntimePipeline now delegates dependency skip checks.")
    print("[OK] _dependency_failed() was intentionally preserved.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())