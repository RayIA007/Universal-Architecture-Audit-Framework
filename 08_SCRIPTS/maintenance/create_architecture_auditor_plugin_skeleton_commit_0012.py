"""
Commit 0012 - Create the Architecture Auditor plugin skeleton.

Creates:
    plugins/architecture/__init__.py
    plugins/architecture/plugin.yaml
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


PATCH_ID = "uaaf-commit-0012-architecture-auditor-plugin-skeleton"
PATCH_VERSION = "1.0.0"

PLUGIN_DIRECTORY = PROJECT_ROOT / "plugins" / "architecture"
INIT_TARGET = PLUGIN_DIRECTORY / "__init__.py"
MANIFEST_TARGET = PLUGIN_DIRECTORY / "plugin.yaml"
MODULE_TARGET = PLUGIN_DIRECTORY / "architecture_auditor.py"

INIT_SOURCE = '''"""Architecture Auditor plugin package."""

from .architecture_auditor import ArchitectureAuditorPlugin, run

__all__ = ["ArchitectureAuditorPlugin", "run"]
'''

MANIFEST_SOURCE = """plugin_id: architecture-auditor
name: Architecture Auditor
version: 1.0.0
entrypoint: architecture_auditor.py
"""

MODULE_SOURCE = '''"""
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


def _write_operation(
    operation_id: str,
    target_file: Path,
    content: str,
) -> PatchOperation:
    return PatchOperation(
        operation_id=operation_id,
        operation_type=PatchOperationType.WRITE_FILE,
        target_file=target_file,
        parameters={
            "content": content,
            "overwrite": False,
        },
        required=True,
    )


def build_patch_plan() -> PatchPlan:
    """Build Commit 0012."""

    return PatchPlan(
        patch_id=PATCH_ID,
        name="Create Architecture Auditor plugin skeleton",
        version=PATCH_VERSION,
        description=(
            "Creates the manifest, package initializer and canonical "
            "AuditResult skeleton for the Architecture Auditor."
        ),
        operations=[
            _write_operation(
                "write-architecture-plugin-init",
                INIT_TARGET,
                INIT_SOURCE,
            ),
            _write_operation(
                "write-architecture-plugin-manifest",
                MANIFEST_TARGET,
                MANIFEST_SOURCE,
            ),
            _write_operation(
                "write-architecture-plugin-module",
                MODULE_TARGET,
                MODULE_SOURCE,
            ),
        ],
        create_backups=True,
        validate_python=True,
    )


def main() -> int:
    """Execute Commit 0012."""

    PLUGIN_DIRECTORY.mkdir(parents=True, exist_ok=True)
    result = PatchEngine().execute(build_patch_plan())

    print()
    print("=" * 72)
    print("UAAF Commit 0012 - Architecture Auditor Plugin Skeleton")
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
        print("[FAIL] Commit 0012 was not applied.")
        if result.error:
            print(f"[FAIL] {result.error}")
        for operation in result.operation_results:
            if operation.error:
                print(
                    f"[FAIL] {operation.operation_id}: "
                    f"{operation.error}"
                )
        return 1

    print()
    print("[ OK ] Commit 0012 applied successfully.")
    print("[ OK ] Architecture Auditor plugin skeleton created.")
    print("[ OK ] Canonical AuditResult output is active.")
    print("[ OK ] Python AST and compilation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())