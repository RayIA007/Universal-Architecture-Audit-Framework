"""
Commit 0009F - Correct Documentation Auditor functional-test word count.

This PatchPlan modifies only:

    08_SCRIPTS/tests/documentation_auditor_functional_test.py

It corrects the deterministic expected total from 10 to 11 words.

Run from the UAAF project root:

    python 08_SCRIPTS/maintenance/patch_documentation_auditor_word_count_commit_0009f.py
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


PATCH_ID = "uaaf-commit-0009f-documentation-word-count"
PATCH_VERSION = "1.0.0"

TARGET_FILE = (
    PROJECT_ROOT
    / "08_SCRIPTS"
    / "tests"
    / "documentation_auditor_functional_test.py"
)

OLD_ASSERTION = 'assert metrics["total_markdown_words"] == 10'
NEW_ASSERTION = 'assert metrics["total_markdown_words"] == 11'


def build_patch_plan() -> PatchPlan:
    """Build Commit 0009F."""

    return PatchPlan(
        patch_id=PATCH_ID,
        name="Correct Documentation Auditor word-count assertion",
        version=PATCH_VERSION,
        description=(
            "Corrects the deterministic functional-test expectation from "
            "10 to 11 Markdown words without modifying plugin behavior."
        ),
        operations=[
            PatchOperation(
                operation_id="correct-total-markdown-word-count",
                operation_type=PatchOperationType.REPLACE_TEXT,
                target_file=TARGET_FILE,
                parameters={
                    "old_text": OLD_ASSERTION,
                    "new_text": NEW_ASSERTION,
                },
                description=(
                    "Update the expected word count to match Python split() "
                    "semantics used by the Documentation Auditor."
                ),
                required=True,
            ),
        ],
        create_backups=True,
        validate_python=True,
    )


def main() -> int:
    """Execute Commit 0009F."""

    if not TARGET_FILE.is_file():
        print(f"[FAIL] Target file not found: {TARGET_FILE}")
        return 1

    result = PatchEngine().execute(build_patch_plan())

    print()
    print("=" * 72)
    print("UAAF Commit 0009F - Documentation Word Count Correction")
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
        print("[FAIL] Commit 0009F was not applied.")
        if result.error:
            print(f"[FAIL] {result.error}")
        return 1

    print()
    print("[ OK ] Commit 0009F applied successfully.")
    print("[ OK ] Expected Markdown word count corrected from 10 to 11.")
    print("[ OK ] Documentation Auditor implementation was not modified.")
    print("[ OK ] Python AST validation passed.")
    print("[ OK ] Python compilation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())