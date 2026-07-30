"""
Pipeline failure handler for the Universal Architecture Audit Framework.

This module centralizes processor-exception recording and the decision to stop
or continue pipeline execution. It deliberately avoids importing pipeline
models so RuntimePipeline can integrate it without circular dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PipelineFailureDecision:
    """Immutable result of evaluating one processor failure."""

    message: str
    should_stop: bool


class PipelineFailureHandler:
    """Record processor failures and evaluate the configured stop policy."""

    @staticmethod
    def handle(
        *,
        processor_id: str,
        error: Exception,
        required: bool,
        stop_on_error: bool,
        execution: Any,
    ) -> PipelineFailureDecision:
        """
        Record a processor exception and return the resulting control decision.

        The execution object must expose the mutable attributes
        ``failed_processor_ids``, ``executed_processor_ids``, and ``errors``.
        """
        if not isinstance(processor_id, str):
            raise TypeError("processor_id must be a string.")

        normalized_processor_id = processor_id.strip()
        if not normalized_processor_id:
            raise ValueError("processor_id cannot be empty.")

        if not isinstance(error, Exception):
            raise TypeError("error must be an Exception instance.")

        if not isinstance(required, bool):
            raise TypeError("required must be a bool.")

        if not isinstance(stop_on_error, bool):
            raise TypeError("stop_on_error must be a bool.")

        PipelineFailureHandler._validate_execution(execution)

        message = (
            f"Processor {normalized_processor_id!r} failed: "
            f"{type(error).__name__}: {str(error).strip()}"
        )

        execution.failed_processor_ids.append(normalized_processor_id)
        execution.executed_processor_ids.append(normalized_processor_id)
        execution.errors.append(message)

        return PipelineFailureDecision(
            message=message,
            should_stop=required and stop_on_error,
        )

    @staticmethod
    def mark_stopped(
        *,
        execution: Any,
        failed_status: Any,
        completed_at: Any,
    ) -> None:
        """
        Mark one execution as terminally failed.

        Status and timestamp types remain owned by RuntimePipeline. This
        handler only applies the terminal state transition, avoiding a
        dependency on pipeline models and preventing circular imports.
        """
        if execution is None:
            raise TypeError("execution cannot be None.")

        if not hasattr(execution, "status"):
            raise TypeError(
                "execution is missing required attribute: status."
            )

        if not hasattr(execution, "completed_at"):
            raise TypeError(
                "execution is missing required attribute: completed_at."
            )

        if failed_status is None:
            raise TypeError("failed_status cannot be None.")

        if completed_at is None:
            raise TypeError("completed_at cannot be None.")

        execution.status = failed_status
        execution.completed_at = completed_at

    @staticmethod
    def _validate_execution(execution: Any) -> None:
        required_attributes = (
            "failed_processor_ids",
            "executed_processor_ids",
            "errors",
        )

        missing = tuple(
            attribute
            for attribute in required_attributes
            if not hasattr(execution, attribute)
        )

        if missing:
            raise TypeError(
                "execution is missing required attributes: "
                f"{', '.join(missing)}."
            )

        invalid = tuple(
            attribute
            for attribute in required_attributes
            if not isinstance(getattr(execution, attribute), list)
        )

        if invalid:
            raise TypeError(
                "execution attributes must be lists: "
                f"{', '.join(invalid)}."
            )


__all__ = [
    "PipelineFailureDecision",
    "PipelineFailureHandler",
]
