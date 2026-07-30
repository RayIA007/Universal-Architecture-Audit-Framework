"""
Processor contract for the Universal Architecture Audit Framework.

This module defines the canonical interface implemented by every UAAF
processor. A processor performs one bounded operation inside an audit
pipeline while remaining independent from the Kernel, Registry, plugins,
and concrete reporting mechanisms.

Concrete processors must implement validation and execution behavior.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, ClassVar

from uaaf_core.models.enums import ProcessorStatus
from uaaf_core.models.session import AuditSession


@dataclass(slots=True)
class ProcessorResult:
    """
    Represent the normalized result of one processor execution.

    Attributes:
        processor_id:
            Identifier of the processor that produced the result.
        status:
            Final execution status.
        started_at:
            UTC timestamp at which execution started.
        completed_at:
            UTC timestamp at which execution ended.
        duration_seconds:
            Total execution duration in seconds.
        outputs:
            Named values produced by the processor.
        warnings:
            Non-critical execution warnings.
        errors:
            Execution errors.
        metadata:
            Additional processor execution information.
    """

    processor_id: str
    status: ProcessorStatus
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    outputs: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and normalize the processor result."""
        self.processor_id = self._normalize_required_string(
            value=self.processor_id,
            field_name="processor_id",
        )

        if not isinstance(self.status, ProcessorStatus):
            raise TypeError(
                "ProcessorResult status must be a ProcessorStatus instance, "
                f"received {type(self.status).__name__}."
            )

        self.started_at = self._normalize_datetime(
            value=self.started_at,
            field_name="started_at",
        )

        self.completed_at = self._normalize_datetime(
            value=self.completed_at,
            field_name="completed_at",
        )

        if self.completed_at < self.started_at:
            raise ValueError(
                "ProcessorResult completed_at cannot be earlier than "
                "started_at."
            )

        if not isinstance(self.duration_seconds, (int, float)):
            raise TypeError(
                "ProcessorResult duration_seconds must be numeric, "
                f"received {type(self.duration_seconds).__name__}."
            )

        self.duration_seconds = float(self.duration_seconds)

        if self.duration_seconds < 0:
            raise ValueError(
                "ProcessorResult duration_seconds cannot be negative."
            )

        if not isinstance(self.outputs, dict):
            raise TypeError(
                "ProcessorResult outputs must be a dictionary, "
                f"received {type(self.outputs).__name__}."
            )

        if not isinstance(self.metadata, dict):
            raise TypeError(
                "ProcessorResult metadata must be a dictionary, "
                f"received {type(self.metadata).__name__}."
            )

        self.warnings = self._normalize_string_list(
            values=self.warnings,
            field_name="warnings",
        )

        self.errors = self._normalize_string_list(
            values=self.errors,
            field_name="errors",
        )

    @property
    def succeeded(self) -> bool:
        """Return whether the processor completed without errors."""
        return not self.errors

    @property
    def has_warnings(self) -> bool:
        """Return whether the processor generated warnings."""
        return bool(self.warnings)

    @property
    def has_errors(self) -> bool:
        """Return whether the processor generated errors."""
        return bool(self.errors)

    @staticmethod
    def _normalize_required_string(
        *,
        value: str,
        field_name: str,
    ) -> str:
        """Validate and normalize a required string."""
        if not isinstance(value, str):
            raise TypeError(
                f"ProcessorResult {field_name} must be a string, "
                f"received {type(value).__name__}."
            )

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(
                f"ProcessorResult {field_name} cannot be empty."
            )

        return normalized_value

    @staticmethod
    def _normalize_datetime(
        *,
        value: datetime,
        field_name: str,
    ) -> datetime:
        """Validate and normalize a timezone-aware datetime to UTC."""
        if not isinstance(value, datetime):
            raise TypeError(
                f"ProcessorResult {field_name} must be a datetime, "
                f"received {type(value).__name__}."
            )

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                f"ProcessorResult {field_name} must include "
                "timezone information."
            )

        return value.astimezone(UTC)

    @classmethod
    def _normalize_string_list(
        cls,
        *,
        values: list[str],
        field_name: str,
    ) -> list[str]:
        """Validate and normalize a list of non-empty strings."""
        if not isinstance(values, list):
            raise TypeError(
                f"ProcessorResult {field_name} must be a list, "
                f"received {type(values).__name__}."
            )

        return [
            cls._normalize_required_string(
                value=value,
                field_name=f"{field_name} item",
            )
            for value in values
        ]


class ProcessorContract(ABC):
    """
    Define the mandatory contract for every UAAF processor.

    Concrete processors must declare a stable processor identifier and
    implement the validate and execute methods.

    The shared run method controls the standard lifecycle:

        initialize
            ↓
        validate
            ↓
        execute
            ↓
        finalize
    """

    processor_id: ClassVar[str]
    processor_version: ClassVar[str] = "1.0.0"
    processor_description: ClassVar[str] = ""

    def __init__(self) -> None:
        """Initialize mutable processor execution state."""
        self._outputs: dict[str, Any] = {}
        self._warnings: list[str] = []
        self._errors: list[str] = []
        self._metadata: dict[str, Any] = {}

        self._validate_contract_metadata()

    @property
    def id(self) -> str:
        """Return the canonical processor identifier."""
        return self.processor_id

    @property
    def version(self) -> str:
        """Return the processor contract version."""
        return self.processor_version

    @property
    def description(self) -> str:
        """Return the human-readable processor description."""
        return self.processor_description

    def initialize(self, session: AuditSession) -> None:
        """
        Initialize processor state before validation.

        Concrete processors may override this method but should call
        ``super().initialize(session)``.
        """
        self._validate_session(session)
        self._reset_execution_state()

    @abstractmethod
    def validate(self, session: AuditSession) -> None:
        """
        Validate whether the processor can execute.

        Implementations must raise an exception when mandatory preconditions
        are not satisfied.

        Args:
            session:
                Active audit session.
        """

    @abstractmethod
    def execute(self, session: AuditSession) -> None:
        """
        Execute the processor operation.

        Implementations should publish results through ``add_output`` and
        report non-fatal conditions through ``add_warning``.

        Args:
            session:
                Active audit session.
        """

    def finalize(self, session: AuditSession) -> None:
        """
        Finalize processor execution.

        Concrete processors may override this method to release resources,
        flush temporary data, or perform local cleanup.
        """
        self._validate_session(session)

    def run(self, session: AuditSession) -> ProcessorResult:
        """
        Execute the complete processor lifecycle.

        Args:
            session:
                Active audit session.

        Returns:
            Normalized ProcessorResult.

        Raises:
            Exception:
                Re-raises any exception produced during initialization,
                validation, execution, or finalization.
        """
        self._validate_session(session)

        started_at = datetime.now(UTC)
        timer_started_at = perf_counter()

        try:
            self.initialize(session)
            self.validate(session)
            self.execute(session)
            self.finalize(session)
        except Exception as error:
            normalized_error = self._format_exception(error)
            self.add_error(normalized_error)

            completed_at = datetime.now(UTC)
            duration_seconds = perf_counter() - timer_started_at

            result = ProcessorResult(
                processor_id=self.processor_id,
                status=ProcessorStatus.FAILED,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration_seconds,
                outputs=dict(self._outputs),
                warnings=list(self._warnings),
                errors=list(self._errors),
                metadata=dict(self._metadata),
            )

            session.add_error(
                f"Processor {self.processor_id!r} failed: "
                f"{normalized_error}"
            )
            session.set_context(
                f"processor_result:{self.processor_id}",
                result,
            )

            raise

        completed_at = datetime.now(UTC)
        duration_seconds = perf_counter() - timer_started_at

        status = (
            ProcessorStatus.COMPLETED_WITH_WARNINGS
            if self._warnings
            else ProcessorStatus.COMPLETED
        )

        result = ProcessorResult(
            processor_id=self.processor_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            outputs=dict(self._outputs),
            warnings=list(self._warnings),
            errors=list(self._errors),
            metadata=dict(self._metadata),
        )

        session.register_processor(self.processor_id)
        session.set_context(
            f"processor_result:{self.processor_id}",
            result,
        )

        for warning in self._warnings:
            session.add_warning(
                f"Processor {self.processor_id!r}: {warning}"
            )

        return result

    def add_output(self, key: str, value: Any) -> None:
        """
        Add or replace one named processor output.

        Args:
            key:
                Non-empty output identifier.
            value:
                Output value.
        """
        normalized_key = self._normalize_required_string(
            value=key,
            field_name="output key",
        )

        self._outputs[normalized_key] = value

    def add_warning(self, warning: str) -> None:
        """Add one non-critical processor warning."""
        normalized_warning = self._normalize_required_string(
            value=warning,
            field_name="warning",
        )

        self._warnings.append(normalized_warning)

    def add_error(self, error: str) -> None:
        """Add one processor execution error."""
        normalized_error = self._normalize_required_string(
            value=error,
            field_name="error",
        )

        self._errors.append(normalized_error)

    def set_metadata(self, key: str, value: Any) -> None:
        """Add or replace one processor metadata value."""
        normalized_key = self._normalize_required_string(
            value=key,
            field_name="metadata key",
        )

        self._metadata[normalized_key] = value

    def _reset_execution_state(self) -> None:
        """Reset mutable state before one execution."""
        self._outputs.clear()
        self._warnings.clear()
        self._errors.clear()
        self._metadata.clear()

    def _validate_contract_metadata(self) -> None:
        """Validate mandatory processor class metadata."""
        self._normalize_required_string(
            value=getattr(self, "processor_id", None),
            field_name="processor_id",
        )

        self._normalize_required_string(
            value=self.processor_version,
            field_name="processor_version",
        )

        if not isinstance(self.processor_description, str):
            raise TypeError(
                "Processor processor_description must be a string, "
                f"received {type(self.processor_description).__name__}."
            )

    @staticmethod
    def _validate_session(session: AuditSession) -> None:
        """Validate the audit session supplied to the processor."""
        if not isinstance(session, AuditSession):
            raise TypeError(
                "Processor session must be an AuditSession instance, "
                f"received {type(session).__name__}."
            )

    @staticmethod
    def _normalize_required_string(
        *,
        value: str,
        field_name: str,
    ) -> str:
        """Validate and normalize a required processor string."""
        if not isinstance(value, str):
            raise TypeError(
                f"Processor {field_name} must be a string, "
                f"received {type(value).__name__}."
            )

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(
                f"Processor {field_name} cannot be empty."
            )

        return normalized_value

    @staticmethod
    def _format_exception(error: Exception) -> str:
        """Return a stable human-readable exception representation."""
        message = str(error).strip()

        if message:
            return f"{type(error).__name__}: {message}"

        return type(error).__name__