"""
PATCH-RUNTIME-PIPELINE-COMMIT-0003C

Remove the obsolete RuntimePipeline._dependency_failed() method.

Run:

    python 08_SCRIPTS/maintenance/patch_runtime_pipeline_commit_0003c.py
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

METHOD_NAME = "_dependency_failed"


def create_backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def locate_method(source: str) -> tuple[int, int] | None:
    tree = ast.parse(source, filename=str(TARGET))

    runtime_pipeline = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "RuntimePipeline"
        ),
        None,
    )

    if runtime_pipeline is None:
        raise RuntimeError(
            "RuntimePipeline class was not found."
        )

    method = next(
        (
            node
            for node in runtime_pipeline.body
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            )
            and node.name == METHOD_NAME
        ),
        None,
    )

    if method is None:
        return None

    start_line = min(
        [method.lineno]
        + [
            decorator.lineno
            for decorator in method.decorator_list
        ]
    )

    if method.end_lineno is None:
        raise RuntimeError(
            "Python AST did not provide the method end line."
        )

    return start_line, method.end_lineno


def remove_method(
    source: str,
    start_line: int,
    end_line: int,
) -> str:
    lines = source.splitlines(keepends=True)

    start_index = start_line - 1
    end_index = end_line

    while (
        end_index < len(lines)
        and lines[end_index].strip() == ""
    ):
        end_index += 1

    updated = "".join(
        lines[:start_index] + lines[end_index:]
    )

    if source.endswith("\n") and not updated.endswith("\n"):
        updated += "\n"

    return updated


def validate_postconditions(source: str) -> None:
    tree = ast.parse(source, filename=str(TARGET))

    runtime_pipeline = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "RuntimePipeline"
        ),
        None,
    )

    if runtime_pipeline is None:
        raise RuntimeError(
            "RuntimePipeline class was not found after patching."
        )

    if any(
        isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
        and node.name == METHOD_NAME
        for node in runtime_pipeline.body
    ):
        raise RuntimeError(
            "_dependency_failed() still exists after patching."
        )

    if "PipelineDependencyGuard.should_skip(" not in source:
        raise RuntimeError(
            "PipelineDependencyGuard integration was not found."
        )


def main() -> int:
    if not TARGET.exists():
        print(f"[ERROR] Target file not found: {TARGET}")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    try:
        location = locate_method(original)
    except Exception as exc:
        print(f"[ERROR] Pre-patch validation failed: {exc}")
        return 1

    if location is None:
        try:
            validate_postconditions(original)
        except Exception as exc:
            print(
                "[ERROR] Method is absent, but postconditions "
                f"are invalid: {exc}"
            )
            return 1

        print("[OK] Patch already applied.")
        return 0

    start_line, end_line = location
    updated = remove_method(
        original,
        start_line,
        end_line,
    )

    try:
        validate_postconditions(updated)
    except Exception as exc:
        print(f"[ERROR] Updated source validation failed: {exc}")
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

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0003C applied successfully.")
    print(f"[OK] Updated: {TARGET}")
    print(f"[OK] Backup: {backup_path}")
    print("[OK] RuntimePipeline._dependency_failed() removed.")
    print("[OK] PipelineDependencyGuard integration preserved.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())