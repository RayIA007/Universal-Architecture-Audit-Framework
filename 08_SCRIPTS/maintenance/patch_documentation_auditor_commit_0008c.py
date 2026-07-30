"""
PATCH-DOCUMENTATION-AUDITOR-COMMIT-0008C

Add minimal documentation-quality findings to the functional auditor.

This commit modifies only:
    plugins/documentation/plugin.py

New checks:
- empty Markdown files
- Markdown files without a level-one heading
- total Markdown lines
- total Markdown words
- aggregate findings count
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
    / "plugins"
    / "documentation"
    / "plugin.py"
)

MODULE_SOURCE = '"""\nFunctional Documentation Auditor MVP.\n\nThe plugin scans a project directory, identifies Markdown files, performs\nminimal content-quality checks, and returns a structured audit result.\n"""\n\nfrom __future__ import annotations\n\nfrom pathlib import Path\nfrom typing import Any\n\n\nIGNORED_DIRECTORY_NAMES = {\n    ".git",\n    ".hg",\n    ".svn",\n    "__pycache__",\n    ".pytest_cache",\n    ".mypy_cache",\n    ".venv",\n    "venv",\n    "node_modules",\n}\n\n\ndef run(context: Any) -> dict[str, Any]:\n    """Scan the target project and return a basic documentation audit."""\n    project_path = _resolve_project_path(context)\n\n    files_scanned = 0\n    markdown_files: list[str] = []\n    empty_markdown_files: list[str] = []\n    markdown_files_without_h1: list[str] = []\n    errors: list[str] = []\n\n    total_lines = 0\n    total_words = 0\n\n    for path in project_path.rglob("*"):\n        if _is_ignored(path, project_path):\n            continue\n\n        if not path.is_file():\n            continue\n\n        files_scanned += 1\n\n        if path.suffix.lower() not in {".md", ".markdown"}:\n            continue\n\n        relative_path = path.relative_to(project_path).as_posix()\n\n        try:\n            content = path.read_text(encoding="utf-8")\n        except (OSError, UnicodeError) as exc:\n            errors.append(f"{relative_path}: {exc}")\n            continue\n\n        markdown_files.append(relative_path)\n\n        stripped_content = content.strip()\n\n        if not stripped_content:\n            empty_markdown_files.append(relative_path)\n            continue\n\n        lines = content.splitlines()\n        total_lines += len(lines)\n        total_words += len(content.split())\n\n        if not _has_level_one_heading(lines):\n            markdown_files_without_h1.append(relative_path)\n\n    findings_count = (\n        len(empty_markdown_files)\n        + len(markdown_files_without_h1)\n        + len(errors)\n    )\n\n    return {\n        "plugin_id": "documentation-auditor",\n        "status": "completed_with_findings" if findings_count else "completed",\n        "project_path": str(project_path),\n        "files_scanned": files_scanned,\n        "markdown_files": sorted(markdown_files),\n        "markdown_file_count": len(markdown_files),\n        "total_markdown_lines": total_lines,\n        "total_markdown_words": total_words,\n        "empty_markdown_files": sorted(empty_markdown_files),\n        "empty_markdown_file_count": len(empty_markdown_files),\n        "markdown_files_without_h1": sorted(markdown_files_without_h1),\n        "markdown_files_without_h1_count": len(\n            markdown_files_without_h1\n        ),\n        "findings_count": findings_count,\n        "errors": errors,\n    }\n\n\ndef _resolve_project_path(context: Any) -> Path:\n    if not isinstance(context, dict):\n        raise TypeError("context must be a dictionary.")\n\n    raw_project_path = context.get("project_path")\n\n    if not isinstance(raw_project_path, (str, Path)):\n        raise ValueError(\n            "context must contain a valid project_path."\n        )\n\n    project_path = Path(raw_project_path).resolve()\n\n    if not project_path.is_dir():\n        raise FileNotFoundError(\n            f"Project directory not found: {project_path}"\n        )\n\n    return project_path\n\n\ndef _is_ignored(path: Path, project_path: Path) -> bool:\n    relative_parts = path.relative_to(project_path).parts\n    return any(\n        part in IGNORED_DIRECTORY_NAMES\n        for part in relative_parts\n    )\n\n\ndef _has_level_one_heading(lines: list[str]) -> bool:\n    return any(\n        line.lstrip().startswith("# ")\n        for line in lines\n    )\n\n\nclass DocumentationAuditorPlugin:\n    """Compatibility wrapper around the functional plugin contract."""\n\n    def execute(self, context: Any) -> dict[str, Any]:\n        return run(context)\n\n\n__all__ = [\n    "DocumentationAuditorPlugin",\n    "run",\n]\n'


def create_backup(path: Path) -> Path | None:
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def validate_source(source: str) -> None:
    tree = ast.parse(source, filename=str(TARGET))

    functions = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    required_functions = {
        "run",
        "_resolve_project_path",
        "_is_ignored",
        "_has_level_one_heading",
    }

    missing = required_functions - functions

    if missing:
        raise RuntimeError(
            "Documentation Auditor is missing functions: "
            f"{', '.join(sorted(missing))}."
        )

    required_fragments = (
        '"total_markdown_lines"',
        '"total_markdown_words"',
        '"empty_markdown_files"',
        '"empty_markdown_file_count"',
        '"markdown_files_without_h1"',
        '"markdown_files_without_h1_count"',
        '"findings_count"',
        '"completed_with_findings"',
    )

    missing_fragments = [
        fragment
        for fragment in required_fragments
        if fragment not in source
    ]

    if missing_fragments:
        raise RuntimeError(
            "Documentation Auditor is missing quality fields: "
            f"{missing_fragments}"
        )


def main() -> int:
    if not TARGET.is_file():
        print(
            "[ERROR] Documentation Auditor plugin not found: "
            f"{TARGET}"
        )
        return 1

    original = TARGET.read_text(encoding="utf-8")

    if original == MODULE_SOURCE:
        validate_source(original)
        py_compile.compile(str(TARGET), doraise=True)

        print("[OK] PATCH-DOCUMENTATION-AUDITOR-COMMIT-0008C already applied.")
        print("[OK] AST validation passed.")
        print("[OK] Compilation validation passed.")
        return 0

    backup_path = create_backup(TARGET)

    try:
        validate_source(MODULE_SOURCE)

        TARGET.write_text(
            MODULE_SOURCE,
            encoding="utf-8",
            newline="",
        )

        py_compile.compile(str(TARGET), doraise=True)
        validate_source(TARGET.read_text(encoding="utf-8"))

    except Exception as exc:
        TARGET.write_text(
            original,
            encoding="utf-8",
            newline="",
        )

        print("[ROLLBACK] Original Documentation Auditor restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")

        if backup_path is not None:
            print(f"[ROLLBACK] Backup preserved at: {backup_path}")

        return 1

    print("[OK] PATCH-DOCUMENTATION-AUDITOR-COMMIT-0008C applied successfully.")
    print(f"[OK] Updated: {TARGET}")

    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")

    print("[OK] Empty Markdown detection added.")
    print("[OK] Missing H1 detection added.")
    print("[OK] Markdown line and word metrics added.")
    print("[OK] Findings aggregation added.")
    print("[OK] Existing Kernel modules were not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())