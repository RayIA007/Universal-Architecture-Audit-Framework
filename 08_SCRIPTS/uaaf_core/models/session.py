"""
Audit session domain model for the Universal Architecture Audit Framework.

This module defines the canonical representation of an isolated UAAF audit
session. A session owns the runtime context, workspace paths, lifecycle state,
processor execution order, warnings, and errors associated with one audit.

Pipeline construction, processor dispatch, filesystem creation, persistence,
and report generation are intentionally outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from uaaf_core.models.audit import Audit
from uaaf_core.models.enums import SessionStatus


@dataclass(slots=True)
class AuditSession:
    """
    Represent an isolated runtime session for one UAAF audit.

    An AuditSession stores the runtime state required while an audit is being
    initialized, executed, finalized, and closed.

    Attributes:
        audit:
            Audit associated with this session.
        workspace_path:
            Isolated working directory for temporary and intermediate data.
        session_id:
            Unique identifier assigned to the session.
        status:
            Current session lifecycle status.
        created_at:
            UTC timestamp at which the session was created.
        opened_at:
            UTC timestamp at which the session was opened.
        started_at:
            UTC timestamp at which execution started.
        closed_at:
            UTC timestamp at which the session was closed.
        context:
            Shared session-level runtime data.
        processor_order:
            Ordered processor identifiers executed by the runtime.
        warnings:
            Non-critical session warnings.
        errors:
            Session errors.
    """

    audit: Audit
    workspace_path: Path

    session_id: UUID = field(default_factory=uuid4)
    status: SessionStatus = SessionStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    opened_at: datetime | None = None
    started_at: datetime | None = None
    closed_at: datetime | None = None
    context: dict[str, Any] = field(default_factory=dict)
    processor_order: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Normalize and validate the minimum session state."""
        if not isinstance(self.audit, Audit):
            raise TypeError(
                "AuditSession audit must be an Audit instance, "
                f"received {type(self.audit).__name__}."
            )

        self.workspace_path = Path(self.workspace_path)

        if not isinstance(self.session_id, UUID):
            raise TypeError(
                "AuditSession session_id must be a UUID instance, "
                f"received {type(self.session_id).__name__}."
            )

        if not isinstance(self.status, SessionStatus):
            raise TypeError(
                "AuditSession status must be a SessionStatus instance, "
                f"received {type(self.status).__name__}."
            )

        self.created_at = self._normalize_datetime(
            value=self.created_at,
            field_name="created_at",
        )

        if self.opened_at is not None:
            self.opened_at = self._normalize_datetime(
                value=self.opened_at,
                field_name="opened_at",
            )

        if self.started_at is not None:
            self.started_at = self._normalize_datetime(
                value=self.started_at,
                field_name="started_at",
            )

        if self.closed_at is not None:
            self.closed_at = self._normalize_datetime(
                value=self.closed_at,
                field_name="closed_at",
            )

        if not isinstance(self.context, dict):
            raise TypeError(
                "AuditSession context must be a dictionary, "
                f"received {type(self.context).__name__}."
            )

        self.processor_order = self._normalize_string_list(
            values=self.processor_order,
            field_name="processor_order",
            allow_duplicates=False,
        )

        self.warnings = self._normalize_string_list(
            values=self.warnings,
            field_name="warnings",
            allow_duplicates=True,
        )

        self.errors = self._normalize_string_list(
            values=self.errors,
            field_name="errors",
            allow_duplicates=True,
        )

        self._validate_timestamp_order()

    @property
    def id(self) -> str:
        """Return the session identifier as a canonical string."""
        return str(self.session_id)

    @property
    def audit_id(self) -> str:
        """Return the associated audit identifier."""
        return self.audit.id

    @property
    def output_path(self) -> Path:
        """Return the output directory owned by the associated audit."""
        return self.audit.output_path

    @property
    def is_open(self) -> bool:
        """Return whether the session is currently open."""
        return self.status in {
            SessionStatus.OPEN,
            SessionStatus.RUNNING,
            SessionStatus.CLOSING,
        }

    @property
    def is_terminal(self) -> bool:
        """Return whether the session reached a terminal status."""
        return self.status in {
            SessionStatus.CLOSED,
            SessionStatus.FAILED,
        }

    @property
    def has_warnings(self) -> bool:
        """Return whether the session contains warnings."""
        return bool(self.warnings)

    @property
    def has_errors(self) -> bool:
        """Return whether the session contains errors."""
        return bool(self.errors)

    @property
    def duration_seconds(self) -> float | None:
        """
        Return the elapsed session execution time in seconds.

        Returns:
            None when execution has not started.
            Elapsed seconds until closure when the session is terminal.
            Elapsed seconds until the current time while execution is active.
        """
        if self.started_at is None:
            return None

        end_time = self.closed_at or datetime.now(UTC)
        return max(0.0, (end_time - self.started_at).total_seconds())

    def open(self, *, opened_at: datetime | None = None) -> None:
        """
        Open the session.

        Args:
            opened_at:
                Optional explicit UTC-compatible opening timestamp.
        """
        self._transition(
            expected={SessionStatus.CREATED},
            new_status=SessionStatus.OPEN,
        )

        self.opened_at = self._normalize_datetime(
            value=opened_at or datetime.now(UTC),
            field_name="opened_at",
        )

        self.closed_at = None
        self._validate_timestamp_order()

    def start(self, *, started_at: datetime | None = None) -> None:
        """
        Start runtime execution for the session.

        Args:
            started_at:
                Optional explicit UTC-compatible start timestamp.
        """
        self._transition(
            expected={SessionStatus.OPEN},
            new_status=SessionStatus.RUNNING,
        )

        self.started_at = self._normalize_datetime(
            value=started_at or datetime.now(UTC),
            field_name="started_at",
        )

        self.closed_at = None
        self._validate_timestamp_order()

    def begin_closing(self) -> None:
        """Move the session from RUNNING or OPEN to CLOSING."""
        self._transition(
            expected={
                SessionStatus.OPEN,
                SessionStatus.RUNNING,
            },
            new_status=SessionStatus.CLOSING,
        )

    def close(self, *, closed_at: datetime | None = None) -> None:
        """
        Close the session successfully.

        Args:
            closed_at:
                Optional explicit UTC-compatible closure timestamp.
        """
        self._transition(
            expected={SessionStatus.CLOSING},
            new_status=SessionStatus.CLOSED,
        )

        self.closed_at = self._normalize_datetime(
            value=closed_at or datetime.now(UTC),
            field_name="closed_at",
        )

        self._validate_timestamp_order()

    def fail(
        self,
        reason: str,
        *,
        closed_at: datetime | None = None,
    ) -> None:
        """
        Mark the session as failed.

        Args:
            reason:
                Human-readable failure reason.
            closed_at:
                Optional explicit UTC-compatible failure timestamp.
        """
        normalized_reason = self._normalize_required_string(
            value=reason,
            field_name="failure reason",
        )

        self._transition(
            expected={
                SessionStatus.CREATED,
                SessionStatus.OPEN,
                SessionStatus.RUNNING,
                SessionStatus.CLOSING,
            },
            new_status=SessionStatus.FAILED,
        )

        self.errors.append(normalized_reason)
        self.closed_at = self._normalize_datetime(
            value=closed_at or datetime.now(UTC),
            field_name="closed_at",
        )

        self._validate_timestamp_order()

    def set_context(self, key: str, value: Any) -> None:
        """
        Add or replace one session context value.

        Args:
            key:
                Non-empty context key.
            value:
                Runtime context value.
        """
        normalized_key = self._normalize_required_string(
            value=key,
            field_name="context key",
        )

        self.context[normalized_key] = value

    def get_context(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Return one context value.

        Args:
            key:
                Context key.
            default:
                Value returned when the key does not exist.
        """
        normalized_key = self._normalize_required_string(
            value=key,
            field_name="context key",
        )

        return self.context.get(normalized_key, default)

    def remove_context(self, key: str) -> Any:
        """
        Remove and return one context value.

        Args:
            key:
                Existing context key.

        Raises:
            KeyError:
                If the key does not exist.
        """
        normalized_key = self._normalize_required_string(
            value=key,
            field_name="context key",
        )

        if normalized_key not in self.context:
            raise KeyError(
                f"AuditSession context key {normalized_key!r} does not exist."
            )

        return self.context.pop(normalized_key)

    def register_processor(self, processor_id: str) -> None:
        """
        Record one processor in execution order.

        A processor identifier may only be registered once per session.

        Args:
            processor_id:
                Unique processor identifier.
        """
        normalized_id = self._normalize_required_string(
            value=processor_id,
            field_name="processor identifier",
        )

        if normalized_id in self.processor_order:
            raise ValueError(
                f"Processor {normalized_id!r} is already registered "
                "in this session."
            )

        self.processor_order.append(normalized_id)

    def add_warning(self, warning: str) -> None:
        """Add one non-critical warning to the session."""
        normalized_warning = self._normalize_required_string(
            value=warning,
            field_name="warning",
        )

        self.warnings.append(normalized_warning)

    def add_error(self, error: str) -> None:
        """Add one error to the session without changing its status."""
        normalized_error = self._normalize_required_string(
            value=error,
            field_name="error",
        )

        self.errors.append(normalized_error)

    def _transition(
        self,
        *,
        expected: set[SessionStatus],
        new_status: SessionStatus,
    ) -> None:
        """
        Apply a validated lifecycle transition.

        Args:
            expected:
                Statuses from which the transition is allowed.
            new_status:
                Destination status.

        Raises:
            ValueError:
                If the current status does not allow the transition.
        """
        if self.status not in expected:
            allowed = ", ".join(
                sorted(status.value for status in expected)
            )

            raise ValueError(
                f"Invalid session transition from {self.status.value!r} "
                f"to {new_status.value!r}. "
                f"Allowed current statuses: {allowed}."
            )

        self.status = new_status

    def _validate_timestamp_order(self) -> None:
        """Validate chronological consistency among session timestamps."""
        if self.opened_at is not None and self.opened_at < self.created_at:
            raise ValueError(
                "AuditSession opened_at cannot be earlier than created_at."
            )

        if self.started_at is not None:
            reference_time = self.opened_at or self.created_at

            if self.started_at < reference_time:
                raise ValueError(
                    "AuditSession started_at cannot be earlier than "
                    "opened_at or created_at."
                )

        if self.closed_at is not None:
            reference_time = (
                self.started_at
                or self.opened_at
                or self.created_at
            )

            if self.closed_at < reference_time:
                raise ValueError(
                    "AuditSession closed_at cannot be earlier than its "
                    "creation, opening, or start timestamp."
                )

    @staticmethod
    def _normalize_datetime(
        *,
        value: datetime,
        field_name: str,
    ) -> datetime:
        """
        Validate and normalize a datetime to UTC.

        Naive datetime values are rejected to prevent ambiguous runtime
        timestamps.
        """
        if not isinstance(value, datetime):
            raise TypeError(
                f"AuditSession {field_name} must be a datetime, "
                f"received {type(value).__name__}."
            )

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                f"AuditSession {field_name} must include "
                "timezone information."
            )

        return value.astimezone(UTC)

    @staticmethod
    def _normalize_required_string(
        *,
        value: str,
        field_name: str,
    ) -> str:
        """Validate and normalize a required string value."""
        if not isinstance(value, str):
            raise TypeError(
                f"AuditSession {field_name} must be a string, "
                f"received {type(value).__name__}."
            )

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(
                f"AuditSession {field_name} cannot be empty."
            )

        return normalized_value

    @classmethod
    def _normalize_string_list(
        cls,
        *,
        values: list[str],
        field_name: str,
        allow_duplicates: bool,
    ) -> list[str]:
        """Validate and normalize a list of required strings."""
        if not isinstance(values, list):
            raise TypeError(
                f"AuditSession {field_name} must be a list, "
                f"received {type(values).__name__}."
            )

        normalized_values: list[str] = []

        for value in values:
            normalized_value = cls._normalize_required_string(
                value=value,
                field_name=f"{field_name} item",
            )

            if (
                not allow_duplicates
                and normalized_value in normalized_values
            ):
                raise ValueError(
                    f"AuditSession {field_name} contains duplicate value "
                    f"{normalized_value!r}."
                )

            normalized_values.append(normalized_value)

        return normalized_values