"""
Architecture Auditor MVP.

This implementation validates its input, discovers Python source files using
stable exclusions, and emits a canonical AuditResult. Semantic architecture
analysis is added in later commits.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from uaaf_core.audit.audit_result import (
    AuditExecution,
    AuditResult,
    AuditStatus,
)


PLUGIN_ID = "architecture-auditor"
PLUGIN_VERSION = "1.0.0"
AUDIT_TYPE = "architecture"

_DEFAULT_IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "node_modules",
        "build",
        "dist",
    }
)

_ALLOWED_CONTEXT_FIELDS = {
    "project_path",
    "audit_type",
    "ignored_directories",
    "forbidden_imports",
    "layers",
    "require_package_initializers",
}


def run(context: Any) -> dict[str, Any]:
    """Discover Python files and return the current architecture audit."""

    project_path, ignored_directories = _validate_context(context)
    python_files = _discover_python_files(
        project_path,
        ignored_directories,
    )

    return AuditResult(
        plugin_id=PLUGIN_ID,
        plugin_version=PLUGIN_VERSION,
        audit_type=AUDIT_TYPE,
        status=AuditStatus.COMPLETED,
        summary={
            "project_path": str(project_path),
            "python_files": python_files,
            "modules": [],
            "packages": [],
            "dependency_cycles": [],
        },
        metrics={
            "python_file_count": len(python_files),
            "module_count": 0,
            "package_count": 0,
            "local_import_count": 0,
            "dependency_edge_count": 0,
            "circular_dependency_count": 0,
            "forbidden_import_count": 0,
            "layer_violation_count": 0,
            "missing_package_initializer_count": 0,
            "findings_count": 0,
        },
        findings=(),
        errors=(),
        execution=AuditExecution(),
    ).to_dict()


def _validate_context(
    context: Any,
) -> tuple[Path, frozenset[str]]:
    """Validate context and return the project path and exclusions."""

    if not isinstance(context, dict):
        raise TypeError("context must be a dictionary.")

    unknown_fields = set(context) - _ALLOWED_CONTEXT_FIELDS
    if unknown_fields:
        raise ValueError(
            "context contains unknown fields: "
            f"{sorted(unknown_fields)}"
        )

    raw_project_path = context.get("project_path")
    if not isinstance(raw_project_path, (str, Path)):
        raise ValueError(
            "context must contain a valid project_path."
        )

    project_path = Path(raw_project_path).expanduser().resolve()
    if not project_path.is_dir():
        raise ValueError(
            f"project_path must reference an existing directory: "
            f"{project_path}"
        )

    audit_type = context.get("audit_type")
    if audit_type is not None and audit_type != AUDIT_TYPE:
        raise ValueError(
            f"audit_type must be {AUDIT_TYPE!r}."
        )

    ignored_directories = _validate_ignored_directories(
        context.get("ignored_directories", [])
    )

    return project_path, ignored_directories


def _validate_ignored_directories(
    value: Any,
) -> frozenset[str]:
    """Validate user exclusions and merge them with the defaults."""

    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError(
            "ignored_directories must be a collection of directory names."
        )

    normalized: set[str] = set(_DEFAULT_IGNORED_DIRECTORIES)

    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                "ignored_directories entries must be non-empty strings."
            )

        directory_name = item.strip()
        if Path(directory_name).name != directory_name:
            raise ValueError(
                "ignored_directories entries must be directory names, "
                f"not paths: {directory_name!r}."
            )

        normalized.add(directory_name)

    return frozenset(normalized)


def _discover_python_files(
    project_path: Path,
    ignored_directories: frozenset[str],
) -> list[str]:
    """Return deterministic POSIX paths for discoverable Python files."""

    discovered: list[str] = []

    for root, directory_names, file_names in os.walk(project_path):
        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in ignored_directories
        )

        root_path = Path(root)
        for file_name in sorted(file_names):
            if not file_name.endswith(".py"):
                continue

            file_path = root_path / file_name
            discovered.append(
                _normalize_relative_path(file_path, project_path)
            )

    return sorted(discovered)


def _normalize_relative_path(
    file_path: Path,
    project_path: Path,
) -> str:
    """Normalize a discovered path as a relative POSIX string."""

    return file_path.relative_to(project_path).as_posix()


class ArchitectureAuditorPlugin:
    """Compatibility wrapper around the functional plugin contract."""

    def execute(self, context: Any) -> dict[str, Any]:
        return run(context)


__all__ = [
    "ArchitectureAuditorPlugin",
    "run",
]
