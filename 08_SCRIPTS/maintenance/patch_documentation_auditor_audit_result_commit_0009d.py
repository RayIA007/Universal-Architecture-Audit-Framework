"""
Commit 0009D - Migrate Documentation Auditor to the canonical AuditResult contract.

Run from the UAAF project root:

    python 08_SCRIPTS/maintenance/patch_documentation_auditor_audit_result_commit_0009d.py
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


PATCH_ID = "uaaf-commit-0009d-documentation-audit-result"
PATCH_VERSION = "1.0.0"

TARGET_FILE = PROJECT_ROOT / "plugins" / "documentation" / "plugin.py"

AUDIT_RESULT_IMPORT = (
    "from uaaf_core.audit.audit_result import "
    "AuditExecution, AuditFinding, AuditResult, AuditStatus, FindingSeverity"
)

LEGACY_RETURN_BLOCK = '''    return {
        "plugin_id": "documentation-auditor",
        "status": "completed_with_findings" if findings_count else "completed",
        "project_path": str(project_path),
        "files_scanned": files_scanned,
        "markdown_files": sorted(markdown_files),
        "markdown_file_count": len(markdown_files),
        "total_markdown_lines": total_lines,
        "total_markdown_words": total_words,
        "empty_markdown_files": sorted(empty_markdown_files),
        "empty_markdown_file_count": len(empty_markdown_files),
        "markdown_files_without_h1": sorted(markdown_files_without_h1),
        "markdown_files_without_h1_count": len(
            markdown_files_without_h1
        ),
        "findings": sorted(
            findings,
            key=lambda item: (item["path"], item["code"]),
        ),
        "findings_count": findings_count,
        "errors": errors,
    }
'''

CANONICAL_RETURN_BLOCK = '''    normalized_findings = tuple(
        AuditFinding(
            code=finding["code"],
            severity=FindingSeverity(finding["severity"]),
            path=finding["path"],
            message=finding["message"],
            details={},
        )
        for finding in sorted(
            findings,
            key=lambda item: (item["path"], item["code"]),
        )
    )

    return AuditResult(
        plugin_id="documentation-auditor",
        plugin_version="1.0.0",
        audit_type="documentation",
        status=(
            AuditStatus.COMPLETED_WITH_FINDINGS
            if findings_count
            else AuditStatus.COMPLETED
        ),
        summary={
            "project_path": str(project_path),
            "markdown_files": sorted(markdown_files),
            "empty_markdown_files": sorted(empty_markdown_files),
            "markdown_files_without_h1": sorted(
                markdown_files_without_h1
            ),
        },
        metrics={
            "files_scanned": files_scanned,
            "markdown_file_count": len(markdown_files),
            "total_markdown_lines": total_lines,
            "total_markdown_words": total_words,
            "empty_markdown_file_count": len(empty_markdown_files),
            "markdown_files_without_h1_count": len(
                markdown_files_without_h1
            ),
            "findings_count": findings_count,
        },
        findings=normalized_findings,
        errors=tuple(errors),
        execution=AuditExecution(),
    ).to_dict()
'''


def build_patch_plan() -> PatchPlan:
    """Build the canonical Commit 0009D PatchPlan."""

    return PatchPlan(
        patch_id=PATCH_ID,
        name="Migrate Documentation Auditor to AuditResult",
        version=PATCH_VERSION,
        description=(
            "Migrates only the Documentation Auditor result payload to the "
            "canonical AuditResult contract while preserving all scan logic."
        ),
        operations=[
            PatchOperation(
                operation_id="ensure-audit-result-import",
                operation_type=PatchOperationType.ENSURE_IMPORT,
                target_file=TARGET_FILE,
                parameters={"import_statement": AUDIT_RESULT_IMPORT},
                description=(
                    "Ensure the Documentation Auditor imports the canonical "
                    "Audit Result classes."
                ),
                required=True,
            ),
            PatchOperation(
                operation_id="replace-legacy-documentation-result",
                operation_type=PatchOperationType.REPLACE_TEXT,
                target_file=TARGET_FILE,
                parameters={
                    "old_text": LEGACY_RETURN_BLOCK,
                    "new_text": CANONICAL_RETURN_BLOCK,
                },
                description=(
                    "Replace only the legacy result dictionary with an "
                    "AuditResult serialization."
                ),
                required=True,
            ),
        ],
        create_backups=True,
        validate_python=True,
    )


def print_result(result: object) -> None:
    """Print a compact and deterministic Patch Engine report."""

    print()
    print("=" * 72)
    print("UAAF Commit 0009D - Documentation Auditor AuditResult Migration")
    print("=" * 72)
    print(f"Patch ID : {result.patch_id}")
    print(f"Version  : {result.patch_version}")
    print(f"Status   : {result.status.value}")
    print(f"Message  : {result.message}")

    if result.error:
        print(f"Error    : {result.error}")

    print()
    print("Summary")
    print("-" * 72)
    print(f"Operations total      : {result.summary.total_operations}")
    print(f"Operations successful : {result.summary.successful_operations}")
    print(f"Operations failed     : {result.summary.failed_operations}")
    print(f"Files changed         : {result.summary.changed_files}")
    print(f"Backups created       : {result.summary.backup_files}")
    print(f"Files rolled back     : {result.summary.rolled_back_files}")
    print("=" * 72)


def main() -> int:
    """Execute Commit 0009D."""

    if not TARGET_FILE.is_file():
        print(f"[FAIL] Target file not found: {TARGET_FILE}")
        return 1

    result = PatchEngine().execute(build_patch_plan())
    print_result(result)

    if result.status is not PatchStatus.SUCCESS:
        print()
        print("[FAIL] Commit 0009D was not applied.")
        return 1

    print()
    print("[ OK ] Commit 0009D applied successfully.")
    print("[ OK ] Documentation Auditor now emits canonical AuditResult payloads.")
    print("[ OK ] Python AST validation passed.")
    print("[ OK ] Python compilation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())