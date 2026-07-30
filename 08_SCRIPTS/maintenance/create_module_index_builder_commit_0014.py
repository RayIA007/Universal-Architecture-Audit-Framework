"""
UAAF Commit 0014 - Module Index Builder

This patch generator will extend the Architecture Auditor with a deterministic
module and package index derived from the Python file inventory introduced by
Commit 0013.

Construction status:
    - 0014A: base generator skeleton
    - 0014B+: Patch Engine integration and Architecture Auditor transformation
"""

from __future__ import annotations

import ast
import py_compile
import sys
from pathlib import Path
from typing import Any


SCRIPT_FILE = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_FILE.parents[2]

TARGET = (
    PROJECT_ROOT
    / "plugins"
    / "architecture"
    / "architecture_auditor.py"
)

PATCH_ID = "uaaf-commit-0014-module-index-builder"
PATCH_TITLE = "UAAF Commit 0014 - Module Index Builder"


SCRIPTS_ROOT = SCRIPT_FILE.parents[1]

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



PATCH_ID = "uaaf-commit-0014-architecture-module-index"
PATCH_NAME = "Add Architecture Auditor module index"
TARGET_FILE = TARGET


OLD_SOURCE = '"""\nArchitecture Auditor MVP.\n\nThis implementation validates its input, discovers Python source files using\nstable exclusions, and emits a canonical AuditResult. Semantic architecture\nanalysis is added in later commits.\n"""\n\nfrom __future__ import annotations\n\nimport os\nfrom pathlib import Path\nfrom typing import Any\n\nfrom uaaf_core.audit.audit_result import (\n    AuditExecution,\n    AuditResult,\n    AuditStatus,\n)\n\n\nPLUGIN_ID = "architecture-auditor"\nPLUGIN_VERSION = "1.0.0"\nAUDIT_TYPE = "architecture"\n\n_DEFAULT_IGNORED_DIRECTORIES = frozenset(\n    {\n        ".git",\n        ".hg",\n        ".svn",\n        "__pycache__",\n        ".pytest_cache",\n        ".mypy_cache",\n        ".venv",\n        "venv",\n        "node_modules",\n        "build",\n        "dist",\n    }\n)\n\n_ALLOWED_CONTEXT_FIELDS = {\n    "project_path",\n    "audit_type",\n    "ignored_directories",\n    "forbidden_imports",\n    "layers",\n    "require_package_initializers",\n}\n\n\ndef run(context: Any) -> dict[str, Any]:\n    """Discover Python files and return the current architecture audit."""\n\n    project_path, ignored_directories = _validate_context(context)\n    python_files = _discover_python_files(\n        project_path,\n        ignored_directories,\n    )\n\n    return AuditResult(\n        plugin_id=PLUGIN_ID,\n        plugin_version=PLUGIN_VERSION,\n        audit_type=AUDIT_TYPE,\n        status=AuditStatus.COMPLETED,\n        summary={\n            "project_path": str(project_path),\n            "python_files": python_files,\n            "modules": [],\n            "packages": [],\n            "dependency_cycles": [],\n        },\n        metrics={\n            "python_file_count": len(python_files),\n            "module_count": 0,\n            "package_count": 0,\n            "local_import_count": 0,\n            "dependency_edge_count": 0,\n            "circular_dependency_count": 0,\n            "forbidden_import_count": 0,\n            "layer_violation_count": 0,\n            "missing_package_initializer_count": 0,\n            "findings_count": 0,\n        },\n        findings=(),\n        errors=(),\n        execution=AuditExecution(),\n    ).to_dict()\n\n\ndef _validate_context(\n    context: Any,\n) -> tuple[Path, frozenset[str]]:\n    """Validate context and return the project path and exclusions."""\n\n    if not isinstance(context, dict):\n        raise TypeError("context must be a dictionary.")\n\n    unknown_fields = set(context) - _ALLOWED_CONTEXT_FIELDS\n    if unknown_fields:\n        raise ValueError(\n            "context contains unknown fields: "\n            f"{sorted(unknown_fields)}"\n        )\n\n    raw_project_path = context.get("project_path")\n    if not isinstance(raw_project_path, (str, Path)):\n        raise ValueError(\n            "context must contain a valid project_path."\n        )\n\n    project_path = Path(raw_project_path).expanduser().resolve()\n    if not project_path.is_dir():\n        raise ValueError(\n            f"project_path must reference an existing directory: "\n            f"{project_path}"\n        )\n\n    audit_type = context.get("audit_type")\n    if audit_type is not None and audit_type != AUDIT_TYPE:\n        raise ValueError(\n            f"audit_type must be {AUDIT_TYPE!r}."\n        )\n\n    ignored_directories = _validate_ignored_directories(\n        context.get("ignored_directories", [])\n    )\n\n    return project_path, ignored_directories\n\n\ndef _validate_ignored_directories(\n    value: Any,\n) -> frozenset[str]:\n    """Validate user exclusions and merge them with the defaults."""\n\n    if not isinstance(value, (list, tuple, set, frozenset)):\n        raise ValueError(\n            "ignored_directories must be a collection of directory names."\n        )\n\n    normalized: set[str] = set(_DEFAULT_IGNORED_DIRECTORIES)\n\n    for item in value:\n        if not isinstance(item, str) or not item.strip():\n            raise ValueError(\n                "ignored_directories entries must be non-empty strings."\n            )\n\n        directory_name = item.strip()\n        if Path(directory_name).name != directory_name:\n            raise ValueError(\n                "ignored_directories entries must be directory names, "\n                f"not paths: {directory_name!r}."\n            )\n\n        normalized.add(directory_name)\n\n    return frozenset(normalized)\n\n\ndef _discover_python_files(\n    project_path: Path,\n    ignored_directories: frozenset[str],\n) -> list[str]:\n    """Return deterministic POSIX paths for discoverable Python files."""\n\n    discovered: list[str] = []\n\n    for root, directory_names, file_names in os.walk(project_path):\n        directory_names[:] = sorted(\n            name\n            for name in directory_names\n            if name not in ignored_directories\n        )\n\n        root_path = Path(root)\n        for file_name in sorted(file_names):\n            if not file_name.endswith(".py"):\n                continue\n\n            file_path = root_path / file_name\n            discovered.append(\n                _normalize_relative_path(file_path, project_path)\n            )\n\n    return sorted(discovered)\n\n\ndef _normalize_relative_path(\n    file_path: Path,\n    project_path: Path,\n) -> str:\n    """Normalize a discovered path as a relative POSIX string."""\n\n    return file_path.relative_to(project_path).as_posix()\n\n\nclass ArchitectureAuditorPlugin:\n    """Compatibility wrapper around the functional plugin contract."""\n\n    def execute(self, context: Any) -> dict[str, Any]:\n        return run(context)\n\n\n__all__ = [\n    "ArchitectureAuditorPlugin",\n    "run",\n]\n'

# PATCH-0014D-APPLIED


NEW_SOURCE_PART_1 = '"""\nArchitecture Auditor MVP.\n\nThis implementation validates its input, discovers Python source files using\nstable exclusions, and builds deterministic module and package indexes without\nreading or parsing Python source contents. Semantic architecture analysis is\nadded in later commits.\n"""\n\nfrom __future__ import annotations\n\nimport os\nfrom pathlib import Path\nfrom typing import Any\n\nfrom uaaf_core.audit.audit_result import (\n    AuditExecution,\n    AuditResult,\n    AuditStatus,\n)\n\n\nPLUGIN_ID = "architecture-auditor"\nPLUGIN_VERSION = "1.1.0"\nAUDIT_TYPE = "architecture"\n\n_DEFAULT_IGNORED_DIRECTORIES = frozenset(\n    {\n        ".git",\n        ".hg",\n        ".svn",\n        "__pycache__",\n        ".pytest_cache",\n        ".mypy_cache",\n        ".venv",\n        "venv",\n        "node_modules",\n        "build",\n        "dist",\n    }\n)\n\n_ALLOWED_CONTEXT_FIELDS = {\n    "project_path",\n    "audit_type",\n    "ignored_directories",\n    "forbidden_imports",\n    "layers",\n    "require_package_initializers",\n}\n\n\ndef run(context: Any) -> dict[str, Any]:\n    """Discover Python files and build normalized module and package indexes."""\n\n    project_path, ignored_directories = _validate_context(context)\n    python_files = _discover_python_files(\n        project_path,\n        ignored_directories,\n    )\n    modules, packages = _build_module_index(python_files)\n\n    return AuditResult(\n        plugin_id=PLUGIN_ID,\n        plugin_version=PLUGIN_VERSION,\n        audit_type=AUDIT_TYPE,\n        status=AuditStatus.COMPLETED,\n        summary={\n            "project_path": str(project_path),\n            "python_files": python_files,\n            "modules": modules,\n            "packages": packages,\n            "dependency_cycles": [],\n        },\n        metrics={\n            "python_file_count": len(python_files),\n            "module_count": len(modules),\n            "package_count": len(packages),\n            "local_import_count": 0,\n            "dependency_edge_count": 0,\n            "circular_dependency_count": 0,\n            "forbidden_import_count": 0,\n            "layer_violation_count": 0,\n            "missing_package_initializer_count": 0,\n            "findings_count": 0,\n        },\n        findings=(),\n        errors=(),\n        execution=AuditExecution(),\n    ).to_dict()\n\n\ndef _validate_context(\n    context: Any,\n) -> tuple[Path, frozenset[str]]:\n    """Validate context and return the project path and exclusions."""\n\n    if not isinstance(context, dict):\n        raise TypeError("context must be a dictionary.")\n\n    unknown_fields = set(context) - _ALLOWED_CONTEXT_FIELDS\n    if unknown_fields:\n        raise ValueError(\n            "context contains unknown fields: "\n            f"{sorted(unknown_fields)}"\n        )\n\n    raw_project_path = context.get("project_path")\n    if not isinstance(raw_project_path, (str, Path)):\n        raise ValueError(\n            "context must contain a valid project_path."\n        )\n\n    project_path = Path(raw_project_path).expanduser().resolve()\n    if not project_path.is_dir():\n        raise ValueError(\n            f"project_path must reference an existing directory: "\n            f"{project_path}"\n        )\n\n    audit_type = context.get("audit_type")\n    if audit_type is not None and audit_type != AUDIT_TYPE:\n        raise ValueError(\n            f"audit_type must be {AUDIT_TYPE!r}."\n        )\n\n    ignored_directories = _validate_ignored_directories(\n        context.get("ignored_directories", [])\n    )\n\n    return project_path, ignored_directories\n\n\ndef _validate_ignored_directories(\n    value: Any,\n) -> frozenset[str]:\n    """Validate user exclusions and merge them with the defaults."""\n\n    if not isinstance(value, (list, tuple, set, frozenset)):\n        raise ValueError(\n            "ignored_directories must be a collection of directory names."\n        )\n\n    normalized: set[str] = set(_DEFAULT_IGNORED_DIRECTORIES)\n\n    for item in value:\n        if not isinstance(item, str) or not item.strip():\n            raise ValueError(\n                "ignored_directories entries must be non-empty strings."\n            )\n\n        directory_name = item.strip()\n        if Path(directory_name).name != directory_name:\n            raise ValueError(\n                "ignored_directories entries must be directory names, "\n                f"not paths: {directory_name!r}."\n            )\n\n        normalized.add(directory_name)\n\n    return frozenset(normalized)\n\n\ndef _discover_python_files(\n    project_path: Path,\n    ignored_directories: frozenset[str],\n) -> list[str]:\n    """Return deterministic POSIX paths for discoverable Python files."""\n\n    discovered: list[str] = []\n\n    for root, directory_names, file_names in os.walk(project_path):\n        directory_names[:] = sorted(\n            name\n            for name in directory_names\n            if name not in ignored_directories\n        )\n\n        root_path = Path(root)\n        for file_name in sorted(file_names):\n            if not file_name.endswith(".py"):\n                continue\n\n            file_path = root_path / file_name\n            discovered.append(\n                _normalize_relative_path(file_path, project_path)\n            )\n\n    return sorted(discovered)\n\n\ndef _normalize_relative_path(\n    file_path: Path,\n    project_path: Path,\n) -> str:\n    """Normalize a discovered path as a relative POSIX string."""\n\n    return file_path.relative_to(project_path).as_posix()\n\n\n'

# PATCH-0014E-APPLIED



NEW_SOURCE_PART_2 = 'def _build_module_index(\n    python_files: list[str],\n) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:\n    """Build deterministic module and package records from Python paths."""\n\n    module_records: list[dict[str, Any]] = []\n    package_modules: dict[str, list[str]] = {}\n    package_paths: dict[str, str] = {}\n\n    for relative_path in sorted(python_files):\n        module_name = _module_name_from_path(relative_path)\n        package_name = _package_name_from_path(relative_path)\n        is_package_initializer = relative_path.endswith("/__init__.py")\n\n        module_records.append(\n            {\n                "name": module_name,\n                "path": relative_path,\n                "package": package_name,\n                "is_package_initializer": is_package_initializer,\n            }\n        )\n\n        if package_name:\n            package_modules.setdefault(package_name, []).append(module_name)\n            package_paths.setdefault(\n                package_name,\n                package_name.replace(".", "/"),\n            )\n\n    package_records = [\n        {\n            "name": package_name,\n            "path": package_paths[package_name],\n            "modules": sorted(package_modules[package_name]),\n        }\n        for package_name in sorted(package_modules)\n    ]\n\n    return module_records, package_records\n\n\ndef _module_name_from_path(relative_path: str) -> str:\n    """Convert a normalized Python path into its dotted module name."""\n\n    path = Path(relative_path)\n    parts = list(path.with_suffix("").parts)\n\n    if parts and parts[-1] == "__init__":\n        parts.pop()\n\n    return ".".join(parts)\n\n\ndef _package_name_from_path(relative_path: str) -> str:\n    """Return the dotted package that owns a normalized Python path."""\n\n    path = Path(relative_path)\n    module_parts = list(path.with_suffix("").parts)\n\n    if module_parts and module_parts[-1] == "__init__":\n        module_parts.pop()\n        return ".".join(module_parts)\n\n    return ".".join(module_parts[:-1])\n\n\nclass ArchitectureAuditorPlugin:\n    """Compatibility wrapper around the functional plugin contract."""\n\n    def execute(self, context: Any) -> dict[str, Any]:\n        return run(context)\n\n\n__all__ = [\n    "ArchitectureAuditorPlugin",\n    "run",\n]\n'


NEW_SOURCE = NEW_SOURCE_PART_1 + NEW_SOURCE_PART_2

# PATCH-0014F-A-APPLIED



# PATCH-0014G-PATCH-PLAN-ANCHOR


# PATCH-0014C-APPLIED



def main() -> int:
    """Execute the completed Commit 0014 patch generator."""
    raise RuntimeError(
        "Commit 0014 generator construction is incomplete. "
        "Apply the remaining 0014 construction patches before execution."
    )


if __name__ == "__main__":
    raise SystemExit(main())
