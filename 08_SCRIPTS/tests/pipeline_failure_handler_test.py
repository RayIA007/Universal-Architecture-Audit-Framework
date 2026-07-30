"""
Focused tests for PipelineFailureHandler.

These tests validate failure recording, stop-policy decisions, terminal-state
updates, and input-contract enforcement independently from RuntimePipeline.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
SCRIPTS_ROOT = SCRIPT_PATH.parents[1]

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


from uaaf_core.runtime.pipeline_failure_handler import (  # noqa: E402
    PipelineFailureDecision,
    PipelineFailureHandler,
)


@dataclass
class FakeExecution:
    failed_processor_ids: list[str] = field(default_factory=list)
    executed_processor_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    status: Any = "running"
    completed_at: datetime | None = None


def assert_raises(
    expected_exception: type[Exception],
    callback: Any,
) -> Exception:
    try:
        callback()
    except expected_exception as error:
        return error

    raise AssertionError(
        f"Expected {expected_exception.__name__} to be raised."
    )


def test_continue_decision() -> None:
    execution = FakeExecution()

    decision = PipelineFailureHandler.handle(
        processor_id="optional-processor",
        error=RuntimeError("optional failure"),
        required=False,
        stop_on_error=True,
        execution=execution,
    )

    assert isinstance(decision, PipelineFailureDecision)
    assert decision.should_stop is False
    assert execution.failed_processor_ids == [
        "optional-processor"
    ]
    assert execution.executed_processor_ids == [
        "optional-processor"
    ]
    assert execution.errors == [
        "Processor 'optional-processor' failed: "
        "RuntimeError: optional failure"
    ]


def test_stop_decision() -> None:
    execution = FakeExecution()

    decision = PipelineFailureHandler.handle(
        processor_id="required-processor",
        error=ValueError("required failure"),
        required=True,
        stop_on_error=True,
        execution=execution,
    )

    assert decision.should_stop is True
    assert decision.message == (
        "Processor 'required-processor' failed: "
        "ValueError: required failure"
    )


def test_continue_on_configured_policy() -> None:
    execution = FakeExecution()

    decision = PipelineFailureHandler.handle(
        processor_id="required-processor",
        error=RuntimeError("continue policy"),
        required=True,
        stop_on_error=False,
        execution=execution,
    )

    assert decision.should_stop is False


def test_mark_stopped() -> None:
    execution = FakeExecution()
    completed_at = datetime.now(UTC)

    PipelineFailureHandler.mark_stopped(
        execution=execution,
        failed_status="failed",
        completed_at=completed_at,
    )

    assert execution.status == "failed"
    assert execution.completed_at is completed_at


def test_input_contracts() -> None:
    execution = FakeExecution()

    assert_raises(
        TypeError,
        lambda: PipelineFailureHandler.handle(
            processor_id=123,
            error=RuntimeError("failure"),
            required=True,
            stop_on_error=True,
            execution=execution,
        ),
    )

    assert_raises(
        ValueError,
        lambda: PipelineFailureHandler.handle(
            processor_id="   ",
            error=RuntimeError("failure"),
            required=True,
            stop_on_error=True,
            execution=execution,
        ),
    )

    assert_raises(
        TypeError,
        lambda: PipelineFailureHandler.handle(
            processor_id="processor",
            error="failure",
            required=True,
            stop_on_error=True,
            execution=execution,
        ),
    )

    assert_raises(
        TypeError,
        lambda: PipelineFailureHandler.handle(
            processor_id="processor",
            error=RuntimeError("failure"),
            required=1,
            stop_on_error=True,
            execution=execution,
        ),
    )

    assert_raises(
        TypeError,
        lambda: PipelineFailureHandler.handle(
            processor_id="processor",
            error=RuntimeError("failure"),
            required=True,
            stop_on_error=1,
            execution=execution,
        ),
    )

    assert_raises(
        TypeError,
        lambda: PipelineFailureHandler.handle(
            processor_id="processor",
            error=RuntimeError("failure"),
            required=True,
            stop_on_error=True,
            execution=object(),
        ),
    )

    assert_raises(
        TypeError,
        lambda: PipelineFailureHandler.mark_stopped(
            execution=object(),
            failed_status="failed",
            completed_at=datetime.now(UTC),
        ),
    )


def main() -> int:
    tests = (
        test_continue_decision,
        test_stop_decision,
        test_continue_on_configured_policy,
        test_mark_stopped,
        test_input_contracts,
    )

    for test in tests:
        test()

    print("[PASS] PipelineFailureHandler focused tests completed.")
    print(f"[PASS] Tests executed: {len(tests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
