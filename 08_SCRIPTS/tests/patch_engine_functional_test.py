"""
Functional test suite for the UAAF Patch Engine.

This module validates the Patch Engine as an integrated component without
modifying real UAAF project files. Every test runs inside an isolated temporary
directory.

Validated capabilities:

1. ReplaceText
2. InsertBefore
3. InsertAfter
4. ReplaceMethodBody
5. EnsureImport
6. WriteFile
7. Backup creation
8. Python AST validation
9. Python compilation validation
10. Failure reporting
11. Rollback
12. Protection against missing target files

Run from the UAAF project root with:

    python 08_SCRIPTS/tests/patch_engine_functional_test.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Callable


# ---------------------------------------------------------------------------
# Import path configuration
# ---------------------------------------------------------------------------

SCRIPT_FILE = Path(__file__).resolve()
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


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------


class FunctionalTestFailure(AssertionError):
    """Raised when a Patch Engine functional assertion fails."""


def assert_true(condition: bool, message: str) -> None:
    """Assert that a condition is true."""

    if not condition:
        raise FunctionalTestFailure(message)


def assert_equal(
    actual: object,
    expected: object,
    message: str,
) -> None:
    """Assert equality and provide useful diagnostic information."""

    if actual != expected:
        raise FunctionalTestFailure(
            f"{message}\n"
            f"Expected: {expected!r}\n"
            f"Actual:   {actual!r}"
        )


def assert_contains(
    content: str,
    expected_fragment: str,
    message: str,
) -> None:
    """Assert that a text fragment exists in content."""

    if expected_fragment not in content:
        raise FunctionalTestFailure(
            f"{message}\n"
            f"Missing fragment: {expected_fragment!r}\n"
            f"Content:\n{content}"
        )


def assert_not_contains(
    content: str,
    unexpected_fragment: str,
    message: str,
) -> None:
    """Assert that a text fragment does not exist in content."""

    if unexpected_fragment in content:
        raise FunctionalTestFailure(
            f"{message}\n"
            f"Unexpected fragment: {unexpected_fragment!r}\n"
            f"Content:\n{content}"
        )


def write_utf8(path: Path, content: str) -> None:
    """Create a UTF-8 test file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_utf8(path: Path) -> str:
    """Read a UTF-8 test file."""

    return path.read_text(encoding="utf-8")


def print_test_header(test_name: str) -> None:
    """Print a standardized test header."""

    print()
    print("-" * 72)
    print(f"TEST: {test_name}")
    print("-" * 72)


def print_test_success(test_name: str) -> None:
    """Print a standardized success message."""

    print(f"[ OK ] {test_name}")


# ---------------------------------------------------------------------------
# Functional test 1
# ---------------------------------------------------------------------------


def test_all_supported_operations() -> None:
    """Validate all six official Patch Engine operations."""

    test_name = "All supported Patch Engine operations"
    print_test_header(test_name)

    with tempfile.TemporaryDirectory(
        prefix="uaaf_patch_engine_operations_"
    ) as temporary_directory:
        workspace = Path(temporary_directory)

        text_file = workspace / "document.txt"
        python_file = workspace / "sample_module.py"
        generated_file = workspace / "generated" / "new_file.txt"

        original_text_content = (
            "HEADER\n"
            "TARGET_LINE\n"
            "FOOTER\n"
        )

        original_python_content = (
            '"""Temporary Python module."""\n'
            "\n"
            "import os\n"
            "\n"
            "\n"
            "class ExampleService:\n"
            '    """Example service used by the functional test."""\n'
            "\n"
            "    def process(self, value: str) -> str:\n"
            '        """Return the original value."""\n'
            "        return value\n"
        )

        write_utf8(text_file, original_text_content)
        write_utf8(python_file, original_python_content)

        operations = [
            PatchOperation(
                operation_id="replace-target-line",
                operation_type=PatchOperationType.REPLACE_TEXT,
                target_file=text_file,
                parameters={
                    "old_text": "TARGET_LINE",
                    "new_text": "REPLACED_LINE",
                },
            ),
            PatchOperation(
                operation_id="insert-before-footer",
                operation_type=PatchOperationType.INSERT_BEFORE,
                target_file=text_file,
                parameters={
                    "anchor": "FOOTER",
                    "content": "BEFORE_FOOTER\n",
                },
            ),
            PatchOperation(
                operation_id="insert-after-header",
                operation_type=PatchOperationType.INSERT_AFTER,
                target_file=text_file,
                parameters={
                    "anchor": "HEADER\n",
                    "content": "AFTER_HEADER\n",
                },
            ),
            PatchOperation(
                operation_id="replace-process-method-body",
                operation_type=PatchOperationType.REPLACE_METHOD_BODY,
                target_file=python_file,
                parameters={
                    "method_name": "process",
                    "class_name": "ExampleService",
                    "new_body": (
                        '"""Return a normalized value."""\n'
                        "normalized = value.strip().upper()\n"
                        "return normalized\n"
                    ),
                },
            ),
            PatchOperation(
                operation_id="ensure-path-import",
                operation_type=PatchOperationType.ENSURE_IMPORT,
                target_file=python_file,
                parameters={
                    "import_statement": "from pathlib import Path",
                },
            ),
            PatchOperation(
                operation_id="write-generated-file",
                operation_type=PatchOperationType.WRITE_FILE,
                target_file=generated_file,
                parameters={
                    "content": (
                        "This file was generated by the UAAF Patch Engine.\n"
                    ),
                    "overwrite": False,
                },
            ),
        ]

        patch_plan = PatchPlan(
            patch_id="functional-all-operations",
            name="Functional test for all official operations",
            description="Validates all six official Patch Engine operations.",
            version="1.0.0",
            operations=operations,
            create_backups=True,
            validate_python=True,
        )

        engine = PatchEngine()
        result = engine.execute(patch_plan)

        assert_equal(
            result.status,
            PatchStatus.SUCCESS,
            "The complete Patch Plan must finish successfully.",
        )

        assert_equal(
            result.patch_id,
            patch_plan.patch_id,
            "PatchResult must preserve the Patch Plan identifier.",
        )

        assert_equal(
            result.patch_version,
            patch_plan.version,
            "PatchResult must preserve the Patch Plan version.",
        )

        assert_equal(
            len(result.operation_results),
            6,
            "The result must contain one result for every operation.",
        )

        for operation_result in result.operation_results:
            assert_equal(
                operation_result.status,
                PatchStatus.SUCCESS,
                (
                    "Every supported operation must complete successfully: "
                    f"{operation_result.operation_id}"
                ),
            )

        patched_text_content = read_utf8(text_file)

        assert_contains(
            patched_text_content,
            "REPLACED_LINE",
            "ReplaceText must insert the replacement text.",
        )

        assert_not_contains(
            patched_text_content,
            "TARGET_LINE",
            "ReplaceText must remove the original target text.",
        )

        assert_contains(
            patched_text_content,
            "BEFORE_FOOTER\nFOOTER",
            "InsertBefore must insert content before its anchor.",
        )

        assert_contains(
            patched_text_content,
            "HEADER\nAFTER_HEADER\n",
            "InsertAfter must insert content after its anchor.",
        )

        patched_python_content = read_utf8(python_file)

        assert_contains(
            patched_python_content,
            "from pathlib import Path",
            "EnsureImport must add the requested import.",
        )

        assert_equal(
            patched_python_content.count(
                "from pathlib import Path"
            ),
            1,
            "EnsureImport must add the import exactly once.",
        )

        assert_contains(
            patched_python_content,
            "normalized = value.strip().upper()",
            "ReplaceMethodBody must insert the new method implementation.",
        )

        assert_contains(
            patched_python_content,
            "return normalized",
            "ReplaceMethodBody must preserve the complete new body.",
        )

        assert_not_contains(
            patched_python_content,
            "return value\n",
            "ReplaceMethodBody must remove the original implementation.",
        )

        assert_true(
            generated_file.exists(),
            "WriteFile must create the requested target file.",
        )

        assert_equal(
            read_utf8(generated_file),
            "This file was generated by the UAAF Patch Engine.\n",
            "WriteFile must preserve the requested content.",
        )

        text_backup = text_file.with_suffix(
            text_file.suffix + ".bak"
        )
        python_backup = python_file.with_suffix(
            python_file.suffix + ".bak"
        )
        generated_backup = generated_file.with_suffix(
            generated_file.suffix + ".bak"
        )

        assert_true(
            text_backup.exists(),
            "The engine must create a backup of an existing text file.",
        )

        assert_true(
            python_backup.exists(),
            "The engine must create a backup of an existing Python file.",
        )

        assert_true(
            not generated_backup.exists(),
            "The engine must not create a backup for a new file.",
        )

        assert_equal(
            read_utf8(text_backup),
            original_text_content,
            "The text backup must contain the original content.",
        )

        assert_equal(
            read_utf8(python_backup),
            original_python_content,
            "The Python backup must contain the original content.",
        )

        assert_equal(
            result.summary.total_operations,
            6,
            "The summary must report six operations.",
        )

        assert_equal(
            result.summary.successful_operations,
            6,
            "The summary must report six successful operations.",
        )

        assert_equal(
            result.summary.failed_operations,
            0,
            "The summary must not report failed operations.",
        )

        assert_equal(
            result.summary.changed_files,
            3,
            "The summary must report all three changed files.",
        )

        assert_equal(
            result.summary.backup_files,
            2,
            "The summary must report backups only for existing files.",
        )

    print_test_success(test_name)


# ---------------------------------------------------------------------------
# Functional test 2
# ---------------------------------------------------------------------------


def test_ensure_import_is_idempotent() -> None:
    """Validate that EnsureImport does not duplicate an existing import."""

    test_name = "EnsureImport idempotence"
    print_test_header(test_name)

    with tempfile.TemporaryDirectory(
        prefix="uaaf_patch_engine_import_"
    ) as temporary_directory:
        workspace = Path(temporary_directory)
        python_file = workspace / "idempotent_module.py"

        original_content = (
            "from pathlib import Path\n"
            "\n"
            "\n"
            "def build_path() -> Path:\n"
            '    return Path(".")\n'
        )

        write_utf8(python_file, original_content)

        patch_plan = PatchPlan(
            patch_id="functional-ensure-import-idempotence",
            name="EnsureImport idempotence test",
            description="Validates that EnsureImport does not duplicate imports.",
            version="1.0.0",
            operations=[
                PatchOperation(
                    operation_id="ensure-existing-import",
                    operation_type=PatchOperationType.ENSURE_IMPORT,
                    target_file=python_file,
                    parameters={
                        "import_statement": "from pathlib import Path",
                    },
                )
            ],
            create_backups=True,
            validate_python=True,
        )

        result = PatchEngine().execute(patch_plan)

        assert_equal(
            result.status,
            PatchStatus.SUCCESS,
            "EnsureImport must succeed when the import already exists.",
        )

        final_content = read_utf8(python_file)

        assert_equal(
            final_content.count("from pathlib import Path"),
            1,
            "EnsureImport must not duplicate an existing import.",
        )

        assert_equal(
            final_content,
            original_content,
            "An idempotent EnsureImport operation must preserve the file.",
        )

        assert_equal(
            result.summary.changed_files,
            0,
            "No file must be reported as changed.",
        )

    print_test_success(test_name)


# ---------------------------------------------------------------------------
# Functional test 3
# ---------------------------------------------------------------------------


def test_python_validation_failure_and_rollback() -> None:
    """Validate rollback when a patch creates invalid Python syntax."""

    test_name = "Python validation failure and rollback"
    print_test_header(test_name)

    with tempfile.TemporaryDirectory(
        prefix="uaaf_patch_engine_rollback_"
    ) as temporary_directory:
        workspace = Path(temporary_directory)
        python_file = workspace / "rollback_module.py"

        original_content = (
            '"""Rollback test module."""\n'
            "\n"
            "\n"
            "def calculate(value: int) -> int:\n"
            "    return value + 1\n"
        )

        write_utf8(python_file, original_content)

        patch_plan = PatchPlan(
            patch_id="functional-invalid-python-rollback",
            name="Invalid Python rollback test",
            description="Validates AST failure reporting and rollback behavior.",
            version="1.0.0",
            operations=[
                PatchOperation(
                    operation_id="introduce-invalid-python",
                    operation_type=PatchOperationType.REPLACE_TEXT,
                    target_file=python_file,
                    parameters={
                        "old_text": "return value + 1",
                        "new_text": "return (value +",
                    },
                )
            ],
            create_backups=True,
            validate_python=True,
        )

        result = PatchEngine().execute(patch_plan)

        assert_equal(
            result.status,
            PatchStatus.FAILED,
            "Invalid Python syntax must fail the Patch Plan.",
        )

        assert_true(
            result.error is not None,
            "A failed Patch Plan must expose an error message.",
        )

        assert_contains(
            result.error or "",
            "AST validation failed",
            "The failure must identify the AST validation stage.",
        )

        assert_equal(
            read_utf8(python_file),
            original_content,
            "Rollback must preserve or restore the original Python file.",
        )

        backup_file = python_file.with_suffix(
            python_file.suffix + ".bak"
        )

        assert_true(
            backup_file.exists(),
            "The original file backup must remain available.",
        )

        assert_equal(
            read_utf8(backup_file),
            original_content,
            "The backup must contain the original valid Python source.",
        )

        assert_equal(
            result.summary.rolled_back_files,
            1,
            "The summary must report the restored file.",
        )

    print_test_success(test_name)


# ---------------------------------------------------------------------------
# Functional test 4
# ---------------------------------------------------------------------------


def test_missing_target_file_failure() -> None:
    """Validate controlled failure for a missing non-WriteFile target."""

    test_name = "Missing target file protection"
    print_test_header(test_name)

    with tempfile.TemporaryDirectory(
        prefix="uaaf_patch_engine_missing_"
    ) as temporary_directory:
        workspace = Path(temporary_directory)
        missing_file = workspace / "missing.txt"

        patch_plan = PatchPlan(
            patch_id="functional-missing-target",
            name="Missing target file test",
            description="Validates controlled failure for a missing target file.",
            version="1.0.0",
            operations=[
                PatchOperation(
                    operation_id="replace-in-missing-file",
                    operation_type=PatchOperationType.REPLACE_TEXT,
                    target_file=missing_file,
                    parameters={
                        "old_text": "old",
                        "new_text": "new",
                    },
                )
            ],
            create_backups=True,
            validate_python=True,
        )

        result = PatchEngine().execute(patch_plan)

        assert_equal(
            result.status,
            PatchStatus.FAILED,
            "A missing target file must fail the Patch Plan.",
        )

        assert_true(
            result.error is not None,
            "The result must include the missing-file error.",
        )

        assert_contains(
            result.error or "",
            "does not exist",
            "The error must explain that the target file does not exist.",
        )

        assert_true(
            not missing_file.exists(),
            "A failed non-WriteFile operation must not create the target.",
        )

    print_test_success(test_name)


# ---------------------------------------------------------------------------
# Functional test 5
# ---------------------------------------------------------------------------


def test_write_file_overwrite_protection() -> None:
    """Validate WriteFile overwrite protection."""

    test_name = "WriteFile overwrite protection"
    print_test_header(test_name)

    with tempfile.TemporaryDirectory(
        prefix="uaaf_patch_engine_overwrite_"
    ) as temporary_directory:
        workspace = Path(temporary_directory)
        existing_file = workspace / "protected.txt"

        original_content = "Original protected content.\n"
        write_utf8(existing_file, original_content)

        patch_plan = PatchPlan(
            patch_id="functional-write-file-protection",
            name="WriteFile overwrite protection test",
            description="Validates WriteFile overwrite protection.",
            version="1.0.0",
            operations=[
                PatchOperation(
                    operation_id="refuse-existing-file-overwrite",
                    operation_type=PatchOperationType.WRITE_FILE,
                    target_file=existing_file,
                    parameters={
                        "content": "Unauthorized replacement.\n",
                        "overwrite": False,
                    },
                )
            ],
            create_backups=True,
            validate_python=True,
        )

        result = PatchEngine().execute(patch_plan)

        assert_equal(
            result.status,
            PatchStatus.FAILED,
            "WriteFile must fail when overwrite is disabled.",
        )

        assert_equal(
            read_utf8(existing_file),
            original_content,
            "The protected file must preserve its original content.",
        )

        assert_equal(
            len(result.operation_results),
            1,
            "The result must include the failed WriteFile operation.",
        )

        assert_equal(
            result.operation_results[0].status,
            PatchStatus.FAILED,
            "The WriteFile operation result must report failure.",
        )

    print_test_success(test_name)


# ---------------------------------------------------------------------------
# Functional test 6
# ---------------------------------------------------------------------------


def test_invalid_patch_plan_rejection() -> None:
    """Validate rejection of a Patch Plan with duplicate operation IDs."""

    test_name = "Invalid Patch Plan rejection"
    print_test_header(test_name)

    with tempfile.TemporaryDirectory(
        prefix="uaaf_patch_engine_invalid_plan_"
    ) as temporary_directory:
        workspace = Path(temporary_directory)
        target_file = workspace / "duplicate_ids.txt"

        original_content = "alpha\nbeta\n"
        write_utf8(target_file, original_content)

        duplicate_operation_id = "duplicate-operation"

        patch_plan = PatchPlan(
            patch_id="functional-duplicate-operation-ids",
            name="Duplicate operation identifiers test",
            description="Validates rejection of duplicate operation identifiers.",
            version="1.0.0",
            operations=[
                PatchOperation(
                    operation_id=duplicate_operation_id,
                    operation_type=PatchOperationType.REPLACE_TEXT,
                    target_file=target_file,
                    parameters={
                        "old_text": "alpha",
                        "new_text": "ALPHA",
                    },
                ),
                PatchOperation(
                    operation_id=duplicate_operation_id,
                    operation_type=PatchOperationType.REPLACE_TEXT,
                    target_file=target_file,
                    parameters={
                        "old_text": "beta",
                        "new_text": "BETA",
                    },
                ),
            ],
            create_backups=True,
            validate_python=True,
        )

        result = PatchEngine().execute(patch_plan)

        assert_equal(
            result.status,
            PatchStatus.FAILED,
            "Duplicate operation identifiers must invalidate the plan.",
        )

        assert_true(
            result.error is not None,
            "The invalid Patch Plan must produce an error message.",
        )

        assert_contains(
            result.error or "",
            "Duplicate operation_id",
            "The error must identify the duplicated operation identifier.",
        )

        assert_equal(
            read_utf8(target_file),
            original_content,
            "Plan validation failure must occur before file modification.",
        )

    print_test_success(test_name)


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------


def run_functional_tests() -> int:
    """Execute the complete Patch Engine functional test suite.

    Returns:
        Process-compatible exit code. Zero means success.
    """

    tests: list[Callable[[], None]] = [
        test_all_supported_operations,
        test_ensure_import_is_idempotent,
        test_python_validation_failure_and_rollback,
        test_missing_target_file_failure,
        test_write_file_overwrite_protection,
        test_invalid_patch_plan_rejection,
    ]

    print()
    print("=" * 72)
    print("UAAF Patch Engine Functional Test Suite")
    print("=" * 72)
    print(f"Tests scheduled: {len(tests)}")

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1

        except Exception as error:
            failed += 1

            print()
            print(f"[FAIL] {test.__name__}")
            print(f"       {type(error).__name__}: {error}")

    print()
    print("=" * 72)
    print("Patch Engine Functional Test Summary")
    print("=" * 72)
    print(f"Total  : {len(tests)}")
    print(f"Passed : {passed}")
    print(f"Failed : {failed}")
    print("=" * 72)

    if failed:
        print()
        print("[FAIL] Patch Engine functional validation failed.")
        return 1

    print()
    print("[ OK ] Patch Engine functional validation completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_functional_tests())