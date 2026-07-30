"""
Commit 0010 - Create the Architecture Auditor specification.

Creates:

    90_SPECIFICATIONS/05_AUDITORS/ARCHITECTURE_AUDITOR_SPECIFICATION.md

The target is protected against accidental overwrite.
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


PATCH_ID = "uaaf-commit-0010-architecture-auditor-specification"
PATCH_VERSION = "1.0.0"

TARGET_FILE = (
    PROJECT_ROOT
    / "90_SPECIFICATIONS"
    / "05_AUDITORS"
    / "ARCHITECTURE_AUDITOR_SPECIFICATION.md"
)

SPECIFICATION = """# Architecture Auditor Specification

**Version:** 1.0.0  
**Status:** MVP

## 1. Objective

Evaluate the structural integrity of a Python project and report deterministic
architecture violations without modifying the audited project.

## 2. Scope

The MVP analyzes local Python modules, packages, imports, dependency cycles and
configured architecture rules.

It does not evaluate documentation, security, performance, code style, external
package vulnerabilities or unused code.

## 3. Input

Required:

- `project_path`: existing project directory.

Optional:

- `ignored_directories`: additional directory names to exclude.
- `forbidden_imports`: import rules that must not occur.
- `layers`: ordered architectural layers and their module patterns.
- `require_package_initializers`: whether package directories require
  `__init__.py`; default `false`.

Unknown configuration fields must produce a validation error.

## 4. Default exclusions

- `.git`
- `.venv`
- `venv`
- `__pycache__`
- `node_modules`
- `build`
- `dist`

User exclusions are added to these defaults.

## 5. Rules

### ARCH_CIRCULAR_DEPENDENCY

Detect a cycle between local Python modules.

Severity: `error`.

One finding is produced per unique normalized cycle.

### ARCH_FORBIDDEN_IMPORT

Detect an import prohibited by `forbidden_imports`.

Severity: `error`.

One finding is produced per source module and prohibited import.

### ARCH_LAYER_VIOLATION

Detect a local dependency that violates the configured layer order.

Severity: `error`.

The rule runs only when `layers` is configured.

### ARCH_MISSING_PACKAGE_INITIALIZER

Detect a package directory without `__init__.py`.

Severity: `warning`.

The rule runs only when `require_package_initializers` is `true`.

## 6. Output

The auditor must always return the canonical `AuditResult`.

Required summary fields:

- `project_path`
- `modules`
- `packages`
- `dependency_cycles`

Required metrics:

- `python_file_count`
- `module_count`
- `package_count`
- `local_import_count`
- `dependency_edge_count`
- `circular_dependency_count`
- `forbidden_import_count`
- `layer_violation_count`
- `missing_package_initializer_count`
- `findings_count`

Every finding must use `AuditFinding` and include a stable code, severity, path,
message and details dictionary.

## 7. Determinism

Files, modules, dependencies, cycles and findings must be sorted before output.

Equivalent cycles must not create duplicate findings.

Imports that cannot be resolved to local modules are counted neither as local
dependencies nor as architecture violations, except when explicitly matched by
a forbidden-import rule.

Syntax or file-read failures must be reported through `errors`; they must not
terminate the complete audit.

## 8. Completion criteria

The MVP is complete when:

- it emits a valid `AuditResult`;
- all four rules have deterministic functional tests;
- default exclusions are verified;
- invalid input and configuration are tested;
- Runtime Pipeline integration passes;
- it has no dependency on another auditor.

Features outside this specification require a new specification version.
"""


def build_patch_plan() -> PatchPlan:
    """Build Commit 0010."""

    return PatchPlan(
        patch_id=PATCH_ID,
        name="Create Architecture Auditor specification",
        version=PATCH_VERSION,
        description=(
            "Creates the concise MVP specification for the Architecture Auditor."
        ),
        operations=[
            PatchOperation(
                operation_id="write-architecture-auditor-specification",
                operation_type=PatchOperationType.WRITE_FILE,
                target_file=TARGET_FILE,
                parameters={
                    "content": SPECIFICATION,
                    "overwrite": False,
                },
                description=(
                    "Create ARCHITECTURE_AUDITOR_SPECIFICATION.md without "
                    "overwriting an existing specification."
                ),
                required=True,
            ),
        ],
        create_backups=True,
        validate_python=True,
    )


def main() -> int:
    """Execute Commit 0010."""

    result = PatchEngine().execute(build_patch_plan())

    print()
    print("=" * 72)
    print("UAAF Commit 0010 - Architecture Auditor Specification")
    print("=" * 72)
    print(f"Patch ID : {result.patch_id}")
    print(f"Message  : {result.message}")
    print()
    print("Summary")
    print("-" * 72)
    print(f"Operations total      : {result.summary.total_operations}")
    print(f"Operations successful : {result.summary.successful_operations}")
    print(f"Operations failed     : {result.summary.failed_operations}")
    print(f"Files changed         : {result.summary.changed_files}")
    print(f"Files rolled back     : {result.summary.rolled_back_files}")
    print("=" * 72)

    if result.status is not PatchStatus.SUCCESS:
        print()
        print("[FAIL] Commit 0010 was not applied.")
        if result.error:
            print(f"[FAIL] {result.error}")
        return 1

    print()
    print("[ OK ] Commit 0010 applied successfully.")
    print(f"[ OK ] Specification: {TARGET_FILE}")
    print("[ OK ] Existing files are protected from overwrite.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())