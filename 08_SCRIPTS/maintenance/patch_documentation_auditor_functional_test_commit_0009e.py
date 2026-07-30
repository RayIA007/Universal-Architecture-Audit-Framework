"""
Commit 0009E - Migrate the Documentation Auditor functional test to AuditResult.

This PatchPlan modifies only:

    08_SCRIPTS/tests/documentation_auditor_functional_test.py

It preserves the deterministic fixture and replaces only the body of
_assert_result() so the test validates the canonical AuditResult contract.

Run from the UAAF project root:

    python 08_SCRIPTS/maintenance/patch_documentation_auditor_functional_test_commit_0009e.py
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


PATCH_ID = "uaaf-commit-0009e-documentation-functional-test"
PATCH_VERSION = "1.0.0"

TARGET_FILE = (
    PROJECT_ROOT
    / "08_SCRIPTS"
    / "tests"
    / "documentation_auditor_functional_test.py"
)

NEW_ASSERT_RESULT_BODY = """
required_keys = {
    "plugin_id",
    "plugin_version",
    "audit_type",
    "status",
    "summary",
    "metrics",
    "findings",
    "errors",
    "execution",
}
assert required_keys.issubset(result)

assert result["plugin_id"] == "documentation-auditor"
assert result["plugin_version"] == "1.0.0"
assert result["audit_type"] == "documentation"
assert result["status"] == "completed_with_findings"

summary = result["summary"]
assert isinstance(summary, dict)
assert summary["project_path"] == str(fixture_root.resolve())
assert summary["markdown_files"] == [
    "README.md",
    "docs/empty.md",
    "docs/missing-h1.markdown",
]
assert summary["empty_markdown_files"] == [
    "docs/empty.md",
]
assert summary["markdown_files_without_h1"] == [
    "docs/missing-h1.markdown",
]
assert "node_modules/ignored.md" not in summary["markdown_files"]

metrics = result["metrics"]
assert isinstance(metrics, dict)
assert metrics["files_scanned"] == 4
assert metrics["markdown_file_count"] == 3
assert metrics["total_markdown_lines"] == 4
assert metrics["total_markdown_words"] == 10
assert metrics["empty_markdown_file_count"] == 1
assert metrics["markdown_files_without_h1_count"] == 1
assert metrics["findings_count"] == 2

assert result["errors"] == []

findings = result["findings"]
assert isinstance(findings, list)

findings_by_code = {
    finding["code"]: finding
    for finding in findings
}

assert set(findings_by_code) == {
    "DOC_EMPTY_FILE",
    "DOC_MISSING_H1",
}

assert findings_by_code["DOC_EMPTY_FILE"] == {
    "code": "DOC_EMPTY_FILE",
    "severity": "warning",
    "path": "docs/empty.md",
    "message": "Markdown file is empty.",
    "details": {},
}

assert findings_by_code["DOC_MISSING_H1"] == {
    "code": "DOC_MISSING_H1",
    "severity": "warning",
    "path": "docs/missing-h1.markdown",
    "message": (
        "Markdown file does not contain a level-one heading."
    ),
    "details": {},
}

execution = result["execution"]
assert isinstance(execution, dict)
"""


def build_patch_plan() -> PatchPlan:
    """Build the canonical Commit 0009E PatchPlan."""

    return PatchPlan(
        patch_id=PATCH_ID,
        name="Migrate Documentation Auditor functional test",
        version=PATCH_VERSION,
        description=(
            "Updates only the Documentation Auditor functional assertions "
            "to validate the canonical AuditResult payload."
        ),
        operations=[
            PatchOperation(
                operation_id="replace-documentation-functional-assertions",
                operation_type=PatchOperationType.REPLACE_METHOD_BODY,
                target_file=TARGET_FILE,
                parameters={
                    "method_name": "_assert_result",
                    "new_body": NEW_ASSERT_RESULT_BODY,
                },
                description=(
                    "Replace legacy top-level result assertions with "
                    "canonical AuditResult contract assertions."
                ),
                required=True,
            ),
        ],
        create_backups=True,
        validate_python=True,
    )


def print_result(result: object) -> None:
    """Print a compact Patch Engine execution report."""

    print()
    print("=" * 72)
    print("UAAF Commit 0009E - Documentation Functional Test Migration")
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


def main() -> int:
    """Execute Commit 0009E."""

    if not TARGET_FILE.is_file():
        print(f"[FAIL] Target file not found: {TARGET_FILE}")
        return 1

    result = PatchEngine().execute(build_patch_plan())
    print_result(result)

    if result.status is not PatchStatus.SUCCESS:
        print()
        print("[FAIL] Commit 0009E was not applied.")
        if result.error:
            print(f"[FAIL] {result.error}")
        return 1

    print()
    print("[ OK ] Commit 0009E applied successfully.")
    print("[ OK ] Only _assert_result() was migrated.")
    print("[ OK ] Test fixture and execution flow remain unchanged.")
    print("[ OK ] Python AST validation passed.")
    print("[ OK ] Python compilation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())