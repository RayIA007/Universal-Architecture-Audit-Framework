"""
Commit 0013 - Add deterministic Python project discovery to the Architecture Auditor.

Modifies only:
    plugins/architecture/architecture_auditor.py
"""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_FILE = Path(__file__).resolve()
SCRIPTS_ROOT = SCRIPT_FILE.parents[1]
PROJECT_ROOT = SCRIPT_FILE.parents[2]

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


from uaaf_tools.patch_engine import (  # noqa: E402
    PatchEngine,
    PatchOperation,
    PatchOperationType,
    PatchPlan,
    PatchStatus,
)


PATCH_ID = "uaaf-commit-0013-architecture-project-discovery"
PATCH_VERSION = "1.0.0"
TARGET_FILE = (
    PROJECT_ROOT
    / "plugins"
    / "architecture"
    / "architecture_auditor.py"
)

OLD_SOURCE = '''"""
Architecture Auditor MVP skeleton.

This initial implementation validates its input and emits an empty canonical
AuditResult. Architecture analysis is added in later commits.
"""

from __future__ import annotations

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

_ALLOWED_CONTEXT_FIELDS = {
    "project_path",
    "audit_type",
    "ignored_directories",
    "forbidden_imports",
    "layers",
    "require_package_initializers",
}


def run(context: Any) -> dict[str, Any]:
    """Validate input and return the initial Architecture Auditor result."""

    project_path = _validate_context(context)

    return AuditResult(
        plugin_id=PLUGIN_ID,
        plugin_version=PLUGIN_VERSION,
        audit_type=AUDIT_TYPE,
        status=AuditStatus.COMPLETED,
        summary={
            "project_path": str(project_path),
            "modules": [],
            "packages": [],
            "dependency_cycles": [],
        },
        metrics={
            "python_file_count": 0,
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


def _validate_context(context: Any) -> Path:
    """Validate the MVP context and return the resolved project path."""

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

    return project_path


class ArchitectureAuditorPlugin:
    """Compatibility wrapper around the functional plugin contract."""

    def execute(self, context: Any) -> dict[str, Any]:
        return run(context)


__all__ = [
    "ArchitectureAuditorPlugin",
    "run",
]
'''

NEW_SOURCE = '''"""
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
'''


def build_patch_plan() -> PatchPlan:
    """Build Commit 0013."""

    return PatchPlan(
        patch_id=PATCH_ID,
        name="Add Architecture Auditor project discovery",
        version=PATCH_VERSION,
        description=(
            "Adds deterministic Python file discovery, default exclusions, "
            "configurable exclusions and the python_file_count metric."
        ),
        operations=[
            PatchOperation(
                operation_id="replace-architecture-auditor-with-discovery",
                operation_type=PatchOperationType.REPLACE_TEXT,
                target_file=TARGET_FILE,
                parameters={
                    "old_text": OLD_SOURCE,
                    "new_text": NEW_SOURCE,
                },
                description=(
                    "Replace the Commit 0012 skeleton with the deterministic "
                    "project-discovery implementation."
                ),
                required=True,
            ),
        ],
        create_backups=True,
        validate_python=True,
    )


def main() -> int:
    """Execute Commit 0013."""

    if not TARGET_FILE.is_file():
        print(f"[FAIL] Target file not found: {TARGET_FILE}")
        return 1

    current_source = TARGET_FILE.read_text(encoding="utf-8")
    if current_source == NEW_SOURCE:
        print("[ OK ] Commit 0013 is already applied.")
        print(f"[ OK ] Target: {TARGET_FILE}")
        return 0

    if current_source != OLD_SOURCE:
        print(f"[FAIL] Unexpected target content: {TARGET_FILE}")
        print("[FAIL] Commit 0013 requires the exact Commit 0012 baseline.")
        return 1

    result = PatchEngine().execute(build_patch_plan())

    print()
    print("=" * 72)
    print("UAAF Commit 0013 - Architecture Project Discovery")
    print("=" * 72)
    print(f"Patch ID : {result.patch_id}")
    print(f"Message  : {result.message}")
    print()
    print(f"Operations total      : {result.summary.total_operations}")
    print(f"Operations successful : {result.summary.successful_operations}")
    print(f"Operations failed     : {result.summary.failed_operations}")
    print(f"Files changed         : {result.summary.changed_files}")
    print(f"Files rolled back     : {result.summary.rolled_back_files}")
    print("=" * 72)

    if result.status is not PatchStatus.SUCCESS:
        print()
        print("[FAIL] Commit 0013 was not applied.")
        if result.error:
            print(f"[FAIL] {result.error}")
        return 1

    print()
    print("[ OK ] Commit 0013 applied successfully.")
    print("[ OK ] Deterministic Python project discovery is active.")
    print("[ OK ] Default and configurable exclusions are active.")
    print("[ OK ] Python AST and compilation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())