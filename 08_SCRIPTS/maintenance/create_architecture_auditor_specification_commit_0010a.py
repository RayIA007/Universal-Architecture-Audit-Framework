"""
Commit 0010A - Safely create the Architecture Auditor specification.

Creates or fills:

    90_SPECIFICATIONS/05_AUDITORS/ARCHITECTURE_AUDITOR_SPECIFICATION.md

Safety rules:
- Missing file: create it.
- Empty file: fill it.
- Identical file: report success without changing it.
- Different non-empty file: refuse to overwrite it.
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


PATCH_ID = "uaaf-commit-0010a-architecture-auditor-specification"
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


def determine_overwrite_mode() -> bool:
    """Allow overwrite only when the existing target is empty."""

    TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not TARGET_FILE.exists():
        return False

    current_content = TARGET_FILE.read_text(encoding="utf-8")

    if current_content == SPECIFICATION:
        print("[ OK ] Specification already contains the requested content.")
        raise SystemExit(0)

    if not current_content.strip():
        return True

    print(f"[FAIL] Refusing to overwrite non-empty file: {TARGET_FILE}")
    print("[FAIL] Its content differs from Commit 0010A.")
    raise SystemExit(1)


def build_patch_plan(*, overwrite: bool) -> PatchPlan:
    """Build Commit 0010A."""

    return PatchPlan(
        patch_id=PATCH_ID,
        name="Create Architecture Auditor specification",
        version=PATCH_VERSION,
        description=(
            "Safely creates or fills the Architecture Auditor MVP specification."
        ),
        operations=[
            PatchOperation(
                operation_id="write-architecture-auditor-specification",
                operation_type=PatchOperationType.WRITE_FILE,
                target_file=TARGET_FILE,
                parameters={
                    "content": SPECIFICATION,
                    "overwrite": overwrite,
                },
                description=(
                    "Create the specification or fill an existing empty file."
                ),
                required=True,
            ),
        ],
        create_backups=True,
        validate_python=True,
    )


def print_result(result: object) -> None:
    """Print Patch Plan and operation diagnostics."""

    print()
    print("=" * 72)
    print("UAAF Commit 0010A - Architecture Auditor Specification")
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

    for operation_result in result.operation_results:
        print()
        print(f"Operation : {operation_result.operation_id}")
        print(f"Status    : {operation_result.status.value}")
        print(f"Changed   : {operation_result.changed}")
        print(f"Message   : {operation_result.message}")
        if operation_result.error:
            print(f"Error     : {operation_result.error}")

    print("=" * 72)


def main() -> int:
    """Execute Commit 0010A."""

    overwrite = determine_overwrite_mode()
    result = PatchEngine().execute(build_patch_plan(overwrite=overwrite))
    print_result(result)

    if result.status is not PatchStatus.SUCCESS:
        print()
        print("[FAIL] Commit 0010A was not applied.")
        if result.error:
            print(f"[FAIL] {result.error}")
        return 1

    print()
    print("[ OK ] Commit 0010A applied successfully.")
    print(f"[ OK ] Specification: {TARGET_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())