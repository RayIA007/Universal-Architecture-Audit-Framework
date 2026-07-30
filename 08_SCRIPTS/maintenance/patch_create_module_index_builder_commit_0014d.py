"""
PATCH-CREATE-MODULE-INDEX-BUILDER-COMMIT-0014D

Insert the exact Commit 0013 Architecture Auditor source into the incremental
Commit 0014 generator.
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

ANCHOR = "# PATCH-0014D-OLD-SOURCE-ANCHOR"

REPLACEMENT = 'OLD_SOURCE = \'"""\\nArchitecture Auditor MVP.\\n\\nThis implementation validates its input, discovers Python source files using\\nstable exclusions, and emits a canonical AuditResult. Semantic architecture\\nanalysis is added in later commits.\\n"""\\n\\nfrom __future__ import annotations\\n\\nimport os\\nfrom pathlib import Path\\nfrom typing import Any\\n\\nfrom uaaf_core.audit.audit_result import (\\n    AuditExecution,\\n    AuditResult,\\n    AuditStatus,\\n)\\n\\n\\nPLUGIN_ID = "architecture-auditor"\\nPLUGIN_VERSION = "1.0.0"\\nAUDIT_TYPE = "architecture"\\n\\n_DEFAULT_IGNORED_DIRECTORIES = frozenset(\\n    {\\n        ".git",\\n        ".hg",\\n        ".svn",\\n        "__pycache__",\\n        ".pytest_cache",\\n        ".mypy_cache",\\n        ".venv",\\n        "venv",\\n        "node_modules",\\n        "build",\\n        "dist",\\n    }\\n)\\n\\n_ALLOWED_CONTEXT_FIELDS = {\\n    "project_path",\\n    "audit_type",\\n    "ignored_directories",\\n    "forbidden_imports",\\n    "layers",\\n    "require_package_initializers",\\n}\\n\\n\\ndef run(context: Any) -> dict[str, Any]:\\n    """Discover Python files and return the current architecture audit."""\\n\\n    project_path, ignored_directories = _validate_context(context)\\n    python_files = _discover_python_files(\\n        project_path,\\n        ignored_directories,\\n    )\\n\\n    return AuditResult(\\n        plugin_id=PLUGIN_ID,\\n        plugin_version=PLUGIN_VERSION,\\n        audit_type=AUDIT_TYPE,\\n        status=AuditStatus.COMPLETED,\\n        summary={\\n            "project_path": str(project_path),\\n            "python_files": python_files,\\n            "modules": [],\\n            "packages": [],\\n            "dependency_cycles": [],\\n        },\\n        metrics={\\n            "python_file_count": len(python_files),\\n            "module_count": 0,\\n            "package_count": 0,\\n            "local_import_count": 0,\\n            "dependency_edge_count": 0,\\n            "circular_dependency_count": 0,\\n            "forbidden_import_count": 0,\\n            "layer_violation_count": 0,\\n            "missing_package_initializer_count": 0,\\n            "findings_count": 0,\\n        },\\n        findings=(),\\n        errors=(),\\n        execution=AuditExecution(),\\n    ).to_dict()\\n\\n\\ndef _validate_context(\\n    context: Any,\\n) -> tuple[Path, frozenset[str]]:\\n    """Validate context and return the project path and exclusions."""\\n\\n    if not isinstance(context, dict):\\n        raise TypeError("context must be a dictionary.")\\n\\n    unknown_fields = set(context) - _ALLOWED_CONTEXT_FIELDS\\n    if unknown_fields:\\n        raise ValueError(\\n            "context contains unknown fields: "\\n            f"{sorted(unknown_fields)}"\\n        )\\n\\n    raw_project_path = context.get("project_path")\\n    if not isinstance(raw_project_path, (str, Path)):\\n        raise ValueError(\\n            "context must contain a valid project_path."\\n        )\\n\\n    project_path = Path(raw_project_path).expanduser().resolve()\\n    if not project_path.is_dir():\\n        raise ValueError(\\n            f"project_path must reference an existing directory: "\\n            f"{project_path}"\\n        )\\n\\n    audit_type = context.get("audit_type")\\n    if audit_type is not None and audit_type != AUDIT_TYPE:\\n        raise ValueError(\\n            f"audit_type must be {AUDIT_TYPE!r}."\\n        )\\n\\n    ignored_directories = _validate_ignored_directories(\\n        context.get("ignored_directories", [])\\n    )\\n\\n    return project_path, ignored_directories\\n\\n\\ndef _validate_ignored_directories(\\n    value: Any,\\n) -> frozenset[str]:\\n    """Validate user exclusions and merge them with the defaults."""\\n\\n    if not isinstance(value, (list, tuple, set, frozenset)):\\n        raise ValueError(\\n            "ignored_directories must be a collection of directory names."\\n        )\\n\\n    normalized: set[str] = set(_DEFAULT_IGNORED_DIRECTORIES)\\n\\n    for item in value:\\n        if not isinstance(item, str) or not item.strip():\\n            raise ValueError(\\n                "ignored_directories entries must be non-empty strings."\\n            )\\n\\n        directory_name = item.strip()\\n        if Path(directory_name).name != directory_name:\\n            raise ValueError(\\n                "ignored_directories entries must be directory names, "\\n                f"not paths: {directory_name!r}."\\n            )\\n\\n        normalized.add(directory_name)\\n\\n    return frozenset(normalized)\\n\\n\\ndef _discover_python_files(\\n    project_path: Path,\\n    ignored_directories: frozenset[str],\\n) -> list[str]:\\n    """Return deterministic POSIX paths for discoverable Python files."""\\n\\n    discovered: list[str] = []\\n\\n    for root, directory_names, file_names in os.walk(project_path):\\n        directory_names[:] = sorted(\\n            name\\n            for name in directory_names\\n            if name not in ignored_directories\\n        )\\n\\n        root_path = Path(root)\\n        for file_name in sorted(file_names):\\n            if not file_name.endswith(".py"):\\n                continue\\n\\n            file_path = root_path / file_name\\n            discovered.append(\\n                _normalize_relative_path(file_path, project_path)\\n            )\\n\\n    return sorted(discovered)\\n\\n\\ndef _normalize_relative_path(\\n    file_path: Path,\\n    project_path: Path,\\n) -> str:\\n    """Normalize a discovered path as a relative POSIX string."""\\n\\n    return file_path.relative_to(project_path).as_posix()\\n\\n\\nclass ArchitectureAuditorPlugin:\\n    """Compatibility wrapper around the functional plugin contract."""\\n\\n    def execute(self, context: Any) -> dict[str, Any]:\\n        return run(context)\\n\\n\\n__all__ = [\\n    "ArchitectureAuditorPlugin",\\n    "run",\\n]\\n\'\n\n# PATCH-0014D-APPLIED'


def backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, destination)
    return destination


def main() -> int:
    if not TARGET.is_file():
        print(f"[ERROR] File not found: {TARGET}")
        print("[ERROR] Apply patches 0014A through 0014C before patch 0014D.")
        return 1

    original = TARGET.read_text(encoding="utf-8")

    if "# PATCH-0014D-APPLIED" in original:
        print("[OK] Patch 0014D already applied.")
        return 0

    if "# PATCH-0014C-APPLIED" not in original:
        print("[ERROR] Patch 0014C has not been applied.")
        return 1

    occurrences = original.count(ANCHOR)
    if occurrences != 1:
        print(
            "[ERROR] Expected exactly one 0014D OLD_SOURCE anchor occurrence, "
            f"found {occurrences}."
        )
        return 1

    patched = original.replace(ANCHOR, REPLACEMENT, 1)

    try:
        ast.parse(patched)
    except SyntaxError as exc:
        print(f"[ERROR] Patched source failed AST validation: {exc}")
        return 1

    backup_file = backup(TARGET)

    try:
        TARGET.write_text(patched, encoding="utf-8", newline="")
        py_compile.compile(str(TARGET), doraise=True)
    except Exception as exc:
        TARGET.write_text(original, encoding="utf-8", newline="")
        print(f"[ROLLBACK] {exc}")
        print(f"[ROLLBACK] Backup: {backup_file}")
        return 1

    print("[OK] PATCH-CREATE-MODULE-INDEX-BUILDER-COMMIT-0014D applied successfully.")
    print(f"[OK] Backup: {backup_file}")
    print("[OK] Exact Commit 0013 OLD_SOURCE added.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")
    print("[NEXT] Apply patch 0014E.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())