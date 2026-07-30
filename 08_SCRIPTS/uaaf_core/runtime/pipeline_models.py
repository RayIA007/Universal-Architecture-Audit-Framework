"""
Pipeline domain models for the Universal Architecture Audit Framework.

This module contains only immutable declarations, lifecycle enumerations, and
execution state models used by the runtime pipeline subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class PipelineStatus(str, Enum):
    """Lifecycle status of one pipeline execution."""

    CREATED = "created"
    VALIDATING = "validating"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineFailurePolicy(str, Enum):
    """Policy applied when one processor raises an exception."""

    STOP_ON_ERROR = "stop_on_error"
    CONTINUE_ON_ERROR = "continue_on_error"


@dataclass(frozen=True, slots=True)
class PipelineStep:
    """Immutable declaration of one processor execution step."""

    processor_id: str
    depends_on: tuple[str, ...] = ()
    enabled: bool = True
    required: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_id = self._normalize_identifier(
            self.processor_id,
            "processor_id",
        )
        normalized_dependencies = tuple(
            self._normalize_identifier(value, "dependency")
            for value in self.depends_on
        )

        if normalized_id in normalized_dependencies:
            raise ValueError(
                f"Pipeline step {normalized_id!r} cannot depend on itself."
            )

        if len(set(normalized_dependencies)) != len(normalized_dependencies):
            raise ValueError(
                f"Pipeline step {normalized_id!r} contains duplicate "
                "dependencies."
            )

        if not isinstance(self.enabled, bool):
            raise TypeError("PipelineStep enabled must be a bool.")

        if not isinstance(self.required, bool):
            raise TypeError("PipelineStep required must be a bool.")

        if not isinstance(self.metadata, dict):
            raise TypeError("PipelineStep metadata must be a dictionary.")

        object.__setattr__(self, "processor_id", normalized_id)
        object.__setattr__(self, "depends_on", normalized_dependencies)
        object.__setattr__(self, "metadata", dict(self.metadata))

    @staticmethod
    def _normalize_identifier(value: str, field_name: str) -> str:
        if not isinstance(value, str):
            raise TypeError(
                f"PipelineStep {field_name} must be a string, "
                f"received {type(value).__name__}."
            )

        normalized = value.strip()
        if not normalized:
            raise ValueError(
                f"PipelineStep {field_name} cannot be empty."
            )

        return normalized


@dataclass(slots=True)
class PipelineExecution:
    """Execution record produced by RuntimePipeline."""

    pipeline_id: str
    status: PipelineStatus = PipelineStatus.CREATED
    started_at: datetime | None = None
    completed_at: datetime | None = None
    ordered_processor_ids: tuple[str, ...] = ()
    executed_processor_ids: list[str] = field(default_factory=list)
    skipped_processor_ids: list[str] = field(default_factory=list)
    failed_processor_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float | None:
        """Return elapsed execution time when available."""
        if self.started_at is None:
            return None

        endpoint = self.completed_at or datetime.now(UTC)
        return max(
            0.0,
            (endpoint - self.started_at).total_seconds(),
        )

    @property
    def succeeded(self) -> bool:
        """Return whether execution completed successfully."""
        return self.status in {
            PipelineStatus.COMPLETED,
            PipelineStatus.COMPLETED_WITH_WARNINGS,
        }

    @property
    def has_warnings(self) -> bool:
        """Return whether execution contains warnings."""
        return bool(self.warnings)

    @property
    def has_errors(self) -> bool:
        """Return whether execution contains errors."""
        return bool(self.errors)

    def snapshot(self) -> dict[str, Any]:
        """Return a serializable execution summary."""
        return {
            "pipeline_id": self.pipeline_id,
            "status": self.status.value,
            "started_at": (
                self.started_at.isoformat()
                if self.started_at is not None
                else None
            ),
            "completed_at": (
                self.completed_at.isoformat()
                if self.completed_at is not None
                else None
            ),
            "duration_seconds": self.duration_seconds,
            "ordered_processor_ids": list(self.ordered_processor_ids),
            "executed_processor_ids": list(self.executed_processor_ids),
            "skipped_processor_ids": list(self.skipped_processor_ids),
            "failed_processor_ids": list(self.failed_processor_ids),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


__all__ = [
    "PipelineExecution",
    "PipelineFailurePolicy",
    "PipelineStatus",
    "PipelineStep",
]