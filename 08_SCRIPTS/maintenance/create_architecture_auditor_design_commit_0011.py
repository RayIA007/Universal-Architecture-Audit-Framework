"""
Commit 0011 - Create the Architecture Auditor design document.

Creates or fills:

    90_SPECIFICATIONS/05_AUDITORS/ARCHITECTURE_AUDITOR_DESIGN.md
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


PATCH_ID = "uaaf-commit-0011-architecture-auditor-design"
PATCH_VERSION = "1.0.0"

TARGET_FILE = (
    PROJECT_ROOT
    / "90_SPECIFICATIONS"
    / "05_AUDITORS"
    / "ARCHITECTURE_AUDITOR_DESIGN.md"
)

DESIGN = """# Architecture Auditor Design

**Version:** 1.0.0  
**Status:** MVP

## 1. Design goal

Implement the Architecture Auditor with the minimum structure required to
support the approved specification without creating a premature shared
framework.

## 2. Plugin structure

```text
plugins/architecture/
├── plugin.yaml
├── __init__.py
└── architecture_auditor.py
```

The MVP remains in one implementation module. Extraction into shared UAAF
components is allowed only after a second auditor requires the same behavior.

## 3. Responsibilities

`architecture_auditor.py` will contain:

- input validation;
- project file discovery;
- Python module indexing;
- AST import extraction;
- local dependency resolution;
- cycle detection;
- configured rule evaluation;
- `AuditFinding` construction;
- canonical `AuditResult` construction.

Internal helper functions are preferred over classes unless persistent state or
a clear interface is required.

## 4. Execution flow

1. Validate `project_path` and optional configuration.
2. Discover Python files using default and user exclusions.
3. Build a deterministic module index.
4. Parse imports with `ast`.
5. Resolve imports that reference local modules.
6. Build the local dependency graph.
7. Evaluate the four MVP rules.
8. Sort findings and output data.
9. Return `AuditResult.to_dict()`.

## 5. Internal data

Use standard Python structures only:

- `dict[str, Path]` for the module index;
- `dict[str, set[str]]` for the dependency graph;
- `list[AuditFinding]` for findings;
- `list[str]` for recoverable errors.

No external graph library is required.

## 6. Rule implementation

Each rule is implemented as one private function:

- `_find_circular_dependencies`
- `_find_forbidden_imports`
- `_find_layer_violations`
- `_find_missing_package_initializers`

Each function receives prepared data and returns findings without reading or
modifying files directly.

## 7. Error handling

- Invalid required input stops execution with a validation error.
- Syntax and file-read failures are added to `errors`.
- One unreadable or invalid Python file must not stop the complete audit.
- The auditor never modifies the audited project.

## 8. Determinism

All file paths, module names, dependencies, cycles, findings and summary lists
must be normalized and sorted before serialization.

Cycle detection must produce one canonical representation per unique cycle.

## 9. Shared-component rule

No reusable scanner, resolver or graph package will be created during this MVP.

A component may move into shared UAAF code only when:

1. a second auditor requires the same behavior; and
2. the extracted interface can be defined without auditor-specific rules.

## 10. Initial implementation sequence

1. Create plugin manifest and skeleton.
2. Add discovery and module indexing.
3. Add import extraction and local dependency graph.
4. Add the four rules.
5. Build canonical `AuditResult`.
6. Add deterministic functional tests.
7. Add Runtime Pipeline integration validation.

Features not required by the approved specification remain out of scope.
"""


def determine_overwrite_mode() -> bool:
    """Allow writing a missing or empty file and protect non-empty content."""

    TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not TARGET_FILE.exists():
        return False

    current_content = TARGET_FILE.read_text(encoding="utf-8")

    if current_content == DESIGN:
        print("[ OK ] Design document already contains the requested content.")
        raise SystemExit(0)

    if not current_content.strip():
        return True

    print(f"[FAIL] Refusing to overwrite non-empty file: {TARGET_FILE}")
    return False


def build_patch_plan(*, overwrite: bool) -> PatchPlan:
    """Build Commit 0011."""

    return PatchPlan(
        patch_id=PATCH_ID,
        name="Create Architecture Auditor design",
        version=PATCH_VERSION,
        description="Creates the concise MVP implementation design.",
        operations=[
            PatchOperation(
                operation_id="write-architecture-auditor-design",
                operation_type=PatchOperationType.WRITE_FILE,
                target_file=TARGET_FILE,
                parameters={
                    "content": DESIGN,
                    "overwrite": overwrite,
                },
                description="Create or fill the Architecture Auditor design.",
                required=True,
            ),
        ],
        create_backups=True,
        validate_python=True,
    )


def main() -> int:
    """Execute Commit 0011."""

    overwrite = determine_overwrite_mode()

    if TARGET_FILE.exists() and TARGET_FILE.read_text(
        encoding="utf-8"
    ).strip() and not overwrite:
        return 1

    result = PatchEngine().execute(build_patch_plan(overwrite=overwrite))

    print()
    print("=" * 72)
    print("UAAF Commit 0011 - Architecture Auditor Design")
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
        print("[FAIL] Commit 0011 was not applied.")
        if result.error:
            print(f"[FAIL] {result.error}")
        return 1

    print()
    print("[ OK ] Commit 0011 applied successfully.")
    print(f"[ OK ] Design: {TARGET_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())