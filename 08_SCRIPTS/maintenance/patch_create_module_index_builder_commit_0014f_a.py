"""
Construction patch 0014F-A for the UAAF Commit 0014 generator.

Adds the second and final Architecture Auditor source segment to
create_module_index_builder_commit_0014.py.
"""

from __future__ import annotations

import ast
import py_compile
import shutil
import sys
from pathlib import Path


SCRIPT_FILE = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_FILE.parents[2]
TARGET = (
    PROJECT_ROOT
    / "08_SCRIPTS"
    / "maintenance"
    / "create_module_index_builder_commit_0014.py"
)
BACKUP = TARGET.with_suffix(TARGET.suffix + ".0014f_a.bak")

PATCH_MARKER = "# PATCH-0014F-A-APPLIED"
ANCHOR = "# PATCH-0014F-NEW-SOURCE-PART-2-ANCHOR"

NEW_SOURCE_PART_2 = '''def _build_module_index(
    python_files: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build deterministic module and package records from Python paths."""

    module_records: list[dict[str, Any]] = []
    package_modules: dict[str, list[str]] = {}
    package_paths: dict[str, str] = {}

    for relative_path in sorted(python_files):
        module_name = _module_name_from_path(relative_path)
        package_name = _package_name_from_path(relative_path)
        is_package_initializer = relative_path.endswith("/__init__.py")

        module_records.append(
            {
                "name": module_name,
                "path": relative_path,
                "package": package_name,
                "is_package_initializer": is_package_initializer,
            }
        )

        if package_name:
            package_modules.setdefault(package_name, []).append(module_name)
            package_paths.setdefault(
                package_name,
                package_name.replace(".", "/"),
            )

    package_records = [
        {
            "name": package_name,
            "path": package_paths[package_name],
            "modules": sorted(package_modules[package_name]),
        }
        for package_name in sorted(package_modules)
    ]

    return module_records, package_records


def _module_name_from_path(relative_path: str) -> str:
    """Convert a normalized Python path into its dotted module name."""

    path = Path(relative_path)
    parts = list(path.with_suffix("").parts)

    if parts and parts[-1] == "__init__":
        parts.pop()

    return ".".join(parts)


def _package_name_from_path(relative_path: str) -> str:
    """Return the dotted package that owns a normalized Python path."""

    path = Path(relative_path)
    module_parts = list(path.with_suffix("").parts)

    if module_parts and module_parts[-1] == "__init__":
        module_parts.pop()
        return ".".join(module_parts)

    return ".".join(module_parts[:-1])


class ArchitectureAuditorPlugin:
    """Compatibility wrapper around the functional plugin contract."""

    def execute(self, context: Any) -> dict[str, Any]:
        return run(context)


__all__ = [
    "ArchitectureAuditorPlugin",
    "run",
]
'''

INSERTION = f'''NEW_SOURCE_PART_2 = {NEW_SOURCE_PART_2!r}\n\n\nNEW_SOURCE = NEW_SOURCE_PART_1 + NEW_SOURCE_PART_2\n\n{PATCH_MARKER}\n'''


def _validate_python(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(path))
    py_compile.compile(str(path), doraise=True)


def _rollback() -> None:
    if BACKUP.exists():
        shutil.copy2(BACKUP, TARGET)


def main() -> int:
    if not TARGET.is_file():
        raise FileNotFoundError(f"Target generator not found: {TARGET}")

    source = TARGET.read_text(encoding="utf-8")

    if PATCH_MARKER in source:
        print("PATCH-CREATE-MODULE-INDEX-BUILDER-COMMIT-0014F-A already applied")
        return 0

    if source.count(ANCHOR) != 1:
        raise RuntimeError(
            f"Expected exactly one anchor {ANCHOR!r}; "
            f"found {source.count(ANCHOR)}."
        )

    shutil.copy2(TARGET, BACKUP)

    try:
        updated = source.replace(ANCHOR, INSERTION, 1)
        TARGET.write_text(updated, encoding="utf-8", newline="\n")
        _validate_python(TARGET)
    except Exception:
        _rollback()
        raise

    print("PATCH-CREATE-MODULE-INDEX-BUILDER-COMMIT-0014F-A applied successfully")
    print(f"Backup created: {BACKUP}")
    print("Commit 0014 NEW_SOURCE part 2 added")
    print("AST validation passed")
    print("Compilation validation passed")
    print("NEXT Apply patch 0014G")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())