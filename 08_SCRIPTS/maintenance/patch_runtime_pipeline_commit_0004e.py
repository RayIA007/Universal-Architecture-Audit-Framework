"""
PATCH-RUNTIME-PIPELINE-COMMIT-0004E

Create focused tests for PipelineFailureHandler.

This closure commit adds an independent test file and does not modify runtime
production modules.
"""

from __future__ import annotations

import ast
import py_compile
import shutil
from datetime import datetime
from pathlib import Path


SCRIPT_FILE = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_FILE.parents[2]

TARGET = (
    PROJECT_ROOT
    / "08_SCRIPTS"
    / "tests"
    / "pipeline_failure_handler_test.py"
)

TEST_SOURCE = '"""\nFocused tests for PipelineFailureHandler.\n\nThese tests validate failure recording, stop-policy decisions, terminal-state\nupdates, and input-contract enforcement independently from RuntimePipeline.\n"""\n\nfrom __future__ import annotations\n\nimport sys\nfrom dataclasses import dataclass, field\nfrom datetime import UTC, datetime\nfrom pathlib import Path\nfrom typing import Any\n\n\nSCRIPT_PATH = Path(__file__).resolve()\nSCRIPTS_ROOT = SCRIPT_PATH.parents[1]\n\nif str(SCRIPTS_ROOT) not in sys.path:\n    sys.path.insert(0, str(SCRIPTS_ROOT))\n\n\nfrom uaaf_core.runtime.pipeline_failure_handler import (  # noqa: E402\n    PipelineFailureDecision,\n    PipelineFailureHandler,\n)\n\n\n@dataclass\nclass FakeExecution:\n    failed_processor_ids: list[str] = field(default_factory=list)\n    executed_processor_ids: list[str] = field(default_factory=list)\n    errors: list[str] = field(default_factory=list)\n    status: Any = "running"\n    completed_at: datetime | None = None\n\n\ndef assert_raises(\n    expected_exception: type[Exception],\n    callback: Any,\n) -> Exception:\n    try:\n        callback()\n    except expected_exception as error:\n        return error\n\n    raise AssertionError(\n        f"Expected {expected_exception.__name__} to be raised."\n    )\n\n\ndef test_continue_decision() -> None:\n    execution = FakeExecution()\n\n    decision = PipelineFailureHandler.handle(\n        processor_id="optional-processor",\n        error=RuntimeError("optional failure"),\n        required=False,\n        stop_on_error=True,\n        execution=execution,\n    )\n\n    assert isinstance(decision, PipelineFailureDecision)\n    assert decision.should_stop is False\n    assert execution.failed_processor_ids == [\n        "optional-processor"\n    ]\n    assert execution.executed_processor_ids == [\n        "optional-processor"\n    ]\n    assert execution.errors == [\n        "Processor \'optional-processor\' failed: "\n        "RuntimeError: optional failure"\n    ]\n\n\ndef test_stop_decision() -> None:\n    execution = FakeExecution()\n\n    decision = PipelineFailureHandler.handle(\n        processor_id="required-processor",\n        error=ValueError("required failure"),\n        required=True,\n        stop_on_error=True,\n        execution=execution,\n    )\n\n    assert decision.should_stop is True\n    assert decision.message == (\n        "Processor \'required-processor\' failed: "\n        "ValueError: required failure"\n    )\n\n\ndef test_continue_on_configured_policy() -> None:\n    execution = FakeExecution()\n\n    decision = PipelineFailureHandler.handle(\n        processor_id="required-processor",\n        error=RuntimeError("continue policy"),\n        required=True,\n        stop_on_error=False,\n        execution=execution,\n    )\n\n    assert decision.should_stop is False\n\n\ndef test_mark_stopped() -> None:\n    execution = FakeExecution()\n    completed_at = datetime.now(UTC)\n\n    PipelineFailureHandler.mark_stopped(\n        execution=execution,\n        failed_status="failed",\n        completed_at=completed_at,\n    )\n\n    assert execution.status == "failed"\n    assert execution.completed_at is completed_at\n\n\ndef test_input_contracts() -> None:\n    execution = FakeExecution()\n\n    assert_raises(\n        TypeError,\n        lambda: PipelineFailureHandler.handle(\n            processor_id=123,\n            error=RuntimeError("failure"),\n            required=True,\n            stop_on_error=True,\n            execution=execution,\n        ),\n    )\n\n    assert_raises(\n        ValueError,\n        lambda: PipelineFailureHandler.handle(\n            processor_id="   ",\n            error=RuntimeError("failure"),\n            required=True,\n            stop_on_error=True,\n            execution=execution,\n        ),\n    )\n\n    assert_raises(\n        TypeError,\n        lambda: PipelineFailureHandler.handle(\n            processor_id="processor",\n            error="failure",\n            required=True,\n            stop_on_error=True,\n            execution=execution,\n        ),\n    )\n\n    assert_raises(\n        TypeError,\n        lambda: PipelineFailureHandler.handle(\n            processor_id="processor",\n            error=RuntimeError("failure"),\n            required=1,\n            stop_on_error=True,\n            execution=execution,\n        ),\n    )\n\n    assert_raises(\n        TypeError,\n        lambda: PipelineFailureHandler.handle(\n            processor_id="processor",\n            error=RuntimeError("failure"),\n            required=True,\n            stop_on_error=1,\n            execution=execution,\n        ),\n    )\n\n    assert_raises(\n        TypeError,\n        lambda: PipelineFailureHandler.handle(\n            processor_id="processor",\n            error=RuntimeError("failure"),\n            required=True,\n            stop_on_error=True,\n            execution=object(),\n        ),\n    )\n\n    assert_raises(\n        TypeError,\n        lambda: PipelineFailureHandler.mark_stopped(\n            execution=object(),\n            failed_status="failed",\n            completed_at=datetime.now(UTC),\n        ),\n    )\n\n\ndef main() -> int:\n    tests = (\n        test_continue_decision,\n        test_stop_decision,\n        test_continue_on_configured_policy,\n        test_mark_stopped,\n        test_input_contracts,\n    )\n\n    for test in tests:\n        test()\n\n    print("[PASS] PipelineFailureHandler focused tests completed.")\n    print(f"[PASS] Tests executed: {len(tests)}")\n    return 0\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'


def create_backup(path: Path) -> Path | None:
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(
        f"{path.name}.{timestamp}.bak"
    )
    shutil.copy2(path, backup_path)
    return backup_path


def validate_source(source: str) -> None:
    tree = ast.parse(source, filename=str(TARGET))

    function_names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    required_functions = {
        "test_continue_decision",
        "test_stop_decision",
        "test_continue_on_configured_policy",
        "test_mark_stopped",
        "test_input_contracts",
        "main",
    }

    missing = required_functions - function_names
    if missing:
        raise RuntimeError(
            "Focused test module is missing functions: "
            f"{', '.join(sorted(missing))}."
        )

    handler_calls = [
        node
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "PipelineFailureHandler"
        )
    ]

    called_methods = {
        node.func.attr
        for node in handler_calls
    }

    if "handle" not in called_methods:
        raise RuntimeError(
            "Focused tests do not exercise "
            "PipelineFailureHandler.handle()."
        )

    if "mark_stopped" not in called_methods:
        raise RuntimeError(
            "Focused tests do not exercise "
            "PipelineFailureHandler.mark_stopped()."
        )


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)

    previous_exists = TARGET.exists()
    original = (
        TARGET.read_text(encoding="utf-8")
        if previous_exists
        else None
    )

    if original == TEST_SOURCE:
        try:
            validate_source(original)
            py_compile.compile(str(TARGET), doraise=True)
        except Exception as exc:
            print(
                "[ERROR] Existing Commit 4E test file is invalid: "
                f"{exc}"
            )
            return 1

        print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0004E already applied.")
        print("[OK] AST validation passed.")
        print("[OK] Compilation validation passed.")
        return 0

    backup_path = create_backup(TARGET)

    try:
        validate_source(TEST_SOURCE)

        TARGET.write_text(
            TEST_SOURCE,
            encoding="utf-8",
            newline="",
        )

        py_compile.compile(str(TARGET), doraise=True)
        validate_source(TARGET.read_text(encoding="utf-8"))

    except Exception as exc:
        if original is None:
            if TARGET.exists():
                TARGET.unlink()
        else:
            TARGET.write_text(
                original,
                encoding="utf-8",
                newline="",
            )

        print("[ROLLBACK] Original test state restored.")
        print(f"[ROLLBACK] Patch failed: {exc}")

        if backup_path is not None:
            print(
                "[ROLLBACK] Backup preserved at: "
                f"{backup_path}"
            )

        return 1

    print("[OK] PATCH-RUNTIME-PIPELINE-COMMIT-0004E applied successfully.")
    print(f"[OK] Created or updated: {TARGET}")

    if backup_path is not None:
        print(f"[OK] Backup: {backup_path}")

    print("[OK] PipelineFailureHandler focused tests created.")
    print("[OK] Runtime production modules were not modified.")
    print("[OK] AST validation passed.")
    print("[OK] Compilation validation passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())