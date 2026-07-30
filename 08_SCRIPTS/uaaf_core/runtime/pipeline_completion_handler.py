"""
Completion handling for RuntimePipeline executions.

This module determines and applies the terminal state of a pipeline after all
enabled processors have been evaluated. It intentionally avoids importing
pipeline models to prevent circular dependencies.
"""

from __future__ import annotations

from typing import Any, Mapping


class PipelineCompletionHandler:
    """Determine and apply the terminal state of a pipeline execution."""

    @staticmethod
    def complete(
        *,
        execution: Any,
        required_by_processor_id: Mapping[str, bool],
        completed_at: Any,
        failed_status: Any,
        warning_status: Any,
        completed_status: Any,
    ) -> Any:
        """
        Apply the final completion timestamp and status.

        Returns:
            The terminal status assigned to execution.
        """
        PipelineCompletionHandler._validate_execution(execution)

        if not isinstance(required_by_processor_id, Mapping):
            raise TypeError(
                "required_by_processor_id must be a mapping."
            )

        for processor_id, required in required_by_processor_id.items():
            if not isinstance(processor_id, str):
                raise TypeError(
                    "required_by_processor_id keys must be strings."
                )

            if not isinstance(required, bool):
                raise TypeError(
                    "required_by_processor_id values must be bool."
                )

        if completed_at is None:
            raise TypeError("completed_at cannot be None.")

        statuses = (
            failed_status,
            warning_status,
            completed_status,
        )

        if any(status is None for status in statuses):
            raise TypeError("Completion statuses cannot be None.")

        failed_processor_ids = tuple(
            execution.failed_processor_ids
        )

        if failed_processor_ids:
            missing_ids = tuple(
                processor_id
                for processor_id in failed_processor_ids
                if processor_id not in required_by_processor_id
            )

            if missing_ids:
                raise KeyError(
                    "Missing required-step declarations for failed "
                    f"processors: {', '.join(missing_ids)}."
                )

            required_failed = any(
                required_by_processor_id[processor_id]
                for processor_id in failed_processor_ids
            )

            terminal_status = (
                failed_status
                if required_failed
                else warning_status
            )
        elif execution.warnings:
            terminal_status = warning_status
        else:
            terminal_status = completed_status

        execution.completed_at = completed_at
        execution.status = terminal_status

        return terminal_status

    @staticmethod
    def _validate_execution(execution: Any) -> None:
        if execution is None:
            raise TypeError("execution cannot be None.")

        required_attributes = (
            "failed_processor_ids",
            "warnings",
            "completed_at",
            "status",
        )

        missing_attributes = tuple(
            attribute
            for attribute in required_attributes
            if not hasattr(execution, attribute)
        )

        if missing_attributes:
            raise TypeError(
                "execution is missing required attributes: "
                f"{', '.join(missing_attributes)}."
            )


__all__ = [
    "PipelineCompletionHandler",
]
