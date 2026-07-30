"""
Runtime context for the Universal Architecture Audit Framework.

This module defines the shared state container used during one UAAF audit
execution. The context exposes the active audit, session, profile, registry,
processor results, runtime metadata, metrics, and temporary shared values.

The RuntimeContext does not execute processors, construct pipelines, manage
plugins, persist data, or control the complete runtime lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING

from uaaf_core.models.audit import Audit
from uaaf_core.models.profile import AuditProfile
from uaaf_core.models.session import AuditSession
from uaaf_core.registry import UAAFRegistry

if TYPE_CHECKING:
    from uaaf_core.contracts.processor import ProcessorResult


@dataclass(slots=True)
class RuntimeContext:
    """
    Represent the shared state of one UAAF runtime execution.

    A RuntimeContext groups the canonical domain objects and mutable execution
    data required by the Runtime, Pipeline, and Processors.

    Attributes:
        audit:
            Audit being executed.
        session:
            Active session associated with the audit.
        profile:
            Audit profile selected for execution.
        registry:
            Registry used to resolve runtime components.
        created_at:
            UTC timestamp at which the context was created.
        shared_state:
            Temporary values shared among runtime components.
        processor_results:
            Processor results indexed by processor identifier.
        metrics:
            Runtime metrics indexed by metric name.
        metadata:
            Additional runtime-level information.
        resources:
            Temporary runtime-owned objects or handles.
    """

    audit: Audit
    session: AuditSession
    profile: AuditProfile
    registry: UAAFRegistry

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    shared_state: dict[str, Any] = field(default_factory=dict)
    processor_results: dict[str, ProcessorResult] = field(
        default_factory=dict
    )
    metrics: dict[str, int | float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    resources: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the initial runtime context."""
        if not isinstance(self.audit, Audit):
            raise TypeError(
                "RuntimeContext audit must be an Audit instance, "
                f"received {type(self.audit).__name__}."
            )

        if not isinstance(self.session, AuditSession):
            raise TypeError(
                "RuntimeContext session must be an AuditSession instance, "
                f"received {type(self.session).__name__}."
            )

        if not isinstance(self.profile, AuditProfile):
            raise TypeError(
                "RuntimeContext profile must be an AuditProfile instance, "
                f"received {type(self.profile).__name__}."
            )

        if not isinstance(self.registry, UAAFRegistry):
            raise TypeError(
                "RuntimeContext registry must be a UAAFRegistry instance, "
                f"received {type(self.registry).__name__}."
            )

        self.created_at = self._normalize_datetime(
            value=self.created_at,
            field_name="created_at",
        )

        self._validate_mapping(
            value=self.shared_state,
            field_name="shared_state",
        )
        self._validate_mapping(
            value=self.processor_results,
            field_name="processor_results",
        )
        self._validate_mapping(
            value=self.metrics,
            field_name="metrics",
        )
        self._validate_mapping(
            value=self.metadata,
            field_name="metadata",
        )
        self._validate_mapping(
            value=self.resources,
            field_name="resources",
        )

        self._validate_relationships()
        self._validate_processor_results()
        self._validate_metrics()

    @property
    def audit_id(self) -> str:
        """Return the active audit identifier."""
        return self.audit.id

    @property
    def session_id(self) -> str:
        """Return the active session identifier."""
        return self.session.id

    @property
    def profile_id(self) -> str:
        """Return the active profile identifier."""
        return self.profile.id

    @property
    def processor_result_count(self) -> int:
        """Return the number of stored processor results."""
        return len(self.processor_results)

    @property
    def has_processor_errors(self) -> bool:
        """Return whether at least one processor result contains errors."""
        return any(
            result.has_errors
            for result in self.processor_results.values()
        )

    @property
    def has_processor_warnings(self) -> bool:
        """Return whether at least one processor result contains warnings."""
        return any(
            result.has_warnings
            for result in self.processor_results.values()
        )

    def set_shared(self, key: str, value: Any) -> None:
        """
        Add or replace one shared runtime value.

        Args:
            key:
                Non-empty shared-state key.
            value:
                Runtime value.
        """
        normalized_key = self._normalize_identifier(
            value=key,
            field_name="shared-state key",
        )

        self.shared_state[normalized_key] = value

    def get_shared(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Return one shared runtime value.

        Args:
            key:
                Shared-state key.
            default:
                Value returned when the key does not exist.
        """
        normalized_key = self._normalize_identifier(
            value=key,
            field_name="shared-state key",
        )

        return self.shared_state.get(normalized_key, default)

    def require_shared(self, key: str) -> Any:
        """
        Return one required shared runtime value.

        Raises:
            KeyError:
                If the key does not exist.
        """
        normalized_key = self._normalize_identifier(
            value=key,
            field_name="shared-state key",
        )

        if normalized_key not in self.shared_state:
            raise KeyError(
                f"RuntimeContext shared-state key "
                f"{normalized_key!r} does not exist."
            )

        return self.shared_state[normalized_key]

    def remove_shared(self, key: str) -> Any:
        """
        Remove and return one shared runtime value.

        Raises:
            KeyError:
                If the key does not exist.
        """
        normalized_key = self._normalize_identifier(
            value=key,
            field_name="shared-state key",
        )

        if normalized_key not in self.shared_state:
            raise KeyError(
                f"RuntimeContext shared-state key "
                f"{normalized_key!r} does not exist."
            )

        return self.shared_state.pop(normalized_key)

    def add_processor_result(
        self,
        result: ProcessorResult,
        *,
        replace: bool = False,
    ) -> None:
        """
        Store one normalized processor result.

        Args:
            result:
                ProcessorResult produced by an executed processor.
            replace:
                Whether an existing result with the same processor identifier
                may be replaced.

        Raises:
            TypeError:
                If result is not a ProcessorResult instance.
            ValueError:
                If the processor result already exists.
        """
        from uaaf_core.contracts.processor import ProcessorResult

        if not isinstance(result, ProcessorResult):
            raise TypeError(
                "RuntimeContext result must be a ProcessorResult instance, "
                f"received {type(result).__name__}."
            )

        processor_id = self._normalize_identifier(
            value=result.processor_id,
            field_name="processor identifier",
        )

        if processor_id in self.processor_results and not replace:
            raise ValueError(
                f"Processor result {processor_id!r} already exists."
            )

        self.processor_results[processor_id] = result

    def has_processor_result(self, processor_id: str) -> bool:
        """Return whether a processor result is stored."""
        normalized_id = self._normalize_identifier(
            value=processor_id,
            field_name="processor identifier",
        )

        return normalized_id in self.processor_results

    def get_processor_result(
        self,
        processor_id: str,
    ) -> ProcessorResult:
        """
        Return one stored processor result.

        Raises:
            KeyError:
                If the result does not exist.
        """
        normalized_id = self._normalize_identifier(
            value=processor_id,
            field_name="processor identifier",
        )

        try:
            return self.processor_results[normalized_id]
        except KeyError as error:
            raise KeyError(
                f"Processor result {normalized_id!r} does not exist."
            ) from error

    def list_processor_results(self) -> tuple[ProcessorResult, ...]:
        """
        Return processor results in session execution order.

        Results not present in the session processor order are appended in
        deterministic identifier order.
        """
        ordered_results: list[ProcessorResult] = []
        included_ids: set[str] = set()

        for processor_id in self.session.processor_order:
            result = self.processor_results.get(processor_id)

            if result is not None:
                ordered_results.append(result)
                included_ids.add(processor_id)

        remaining_ids = sorted(
            processor_id
            for processor_id in self.processor_results
            if processor_id not in included_ids
        )

        ordered_results.extend(
            self.processor_results[processor_id]
            for processor_id in remaining_ids
        )

        return tuple(ordered_results)

    def set_metric(
        self,
        name: str,
        value: int | float,
    ) -> None:
        """
        Add or replace one runtime metric.

        Args:
            name:
                Non-empty metric identifier.
            value:
                Numeric metric value.
        """
        normalized_name = self._normalize_identifier(
            value=name,
            field_name="metric name",
        )

        normalized_value = self._normalize_metric_value(
            value=value,
            field_name=normalized_name,
        )

        self.metrics[normalized_name] = normalized_value

    def increment_metric(
        self,
        name: str,
        amount: int | float = 1,
    ) -> int | float:
        """
        Increase one numeric metric and return its new value.

        Missing metrics begin at zero.
        """
        normalized_name = self._normalize_identifier(
            value=name,
            field_name="metric name",
        )

        normalized_amount = self._normalize_metric_value(
            value=amount,
            field_name=f"{normalized_name} increment",
        )

        current_value = self.metrics.get(normalized_name, 0)
        new_value = current_value + normalized_amount

        self.metrics[normalized_name] = new_value
        return new_value

    def get_metric(
        self,
        name: str,
        default: int | float | None = None,
    ) -> int | float | None:
        """Return one runtime metric."""
        normalized_name = self._normalize_identifier(
            value=name,
            field_name="metric name",
        )

        return self.metrics.get(normalized_name, default)

    def set_metadata(self, key: str, value: Any) -> None:
        """Add or replace one runtime metadata value."""
        normalized_key = self._normalize_identifier(
            value=key,
            field_name="metadata key",
        )

        self.metadata[normalized_key] = value

    def get_metadata(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Return one runtime metadata value."""
        normalized_key = self._normalize_identifier(
            value=key,
            field_name="metadata key",
        )

        return self.metadata.get(normalized_key, default)

    def register_resource(
        self,
        resource_id: str,
        resource: Any,
        *,
        replace: bool = False,
    ) -> None:
        """
        Register one temporary runtime resource.

        Args:
            resource_id:
                Unique runtime resource identifier.
            resource:
                Resource object or handle.
            replace:
                Whether an existing resource may be replaced.
        """
        normalized_id = self._normalize_identifier(
            value=resource_id,
            field_name="resource identifier",
        )

        if normalized_id in self.resources and not replace:
            raise ValueError(
                f"Runtime resource {normalized_id!r} already exists."
            )

        self.resources[normalized_id] = resource

    def get_resource(self, resource_id: str) -> Any:
        """
        Return one registered runtime resource.

        Raises:
            KeyError:
                If the resource does not exist.
        """
        normalized_id = self._normalize_identifier(
            value=resource_id,
            field_name="resource identifier",
        )

        try:
            return self.resources[normalized_id]
        except KeyError as error:
            raise KeyError(
                f"Runtime resource {normalized_id!r} does not exist."
            ) from error

    def release_resource(self, resource_id: str) -> Any:
        """
        Remove and return one runtime resource.

        Resource cleanup remains the responsibility of the Runtime or the
        component that owns the resource.
        """
        normalized_id = self._normalize_identifier(
            value=resource_id,
            field_name="resource identifier",
        )

        if normalized_id not in self.resources:
            raise KeyError(
                f"Runtime resource {normalized_id!r} does not exist."
            )

        return self.resources.pop(normalized_id)

    def clear_transient_state(self) -> None:
        """
        Remove temporary shared values and resources.

        Processor results, metrics, and metadata are retained because they
        form part of the execution record.
        """
        self.shared_state.clear()
        self.resources.clear()

    def snapshot(self) -> dict[str, Any]:
        """
        Return a serializable summary of the runtime context.

        Arbitrary shared values and resource objects are represented only by
        their identifiers to avoid exposing non-serializable runtime objects.
        """
        return {
            "audit_id": self.audit_id,
            "session_id": self.session_id,
            "profile_id": self.profile_id,
            "created_at": self.created_at.isoformat(),
            "processor_results": {
                processor_id: {
                    "status": result.status.value,
                    "duration_seconds": result.duration_seconds,
                    "warning_count": len(result.warnings),
                    "error_count": len(result.errors),
                    "output_keys": sorted(result.outputs),
                }
                for processor_id, result
                in sorted(self.processor_results.items())
            },
            "metrics": dict(sorted(self.metrics.items())),
            "metadata": dict(self.metadata),
            "shared_state_keys": sorted(self.shared_state),
            "resource_ids": sorted(self.resources),
        }

    def _validate_relationships(self) -> None:
        """Validate consistency among audit, session, profile, and registry."""
        if self.session.audit.id != self.audit.id:
            raise ValueError(
                "RuntimeContext session does not belong to the supplied "
                "audit."
            )

        if self.audit.profile_id != self.profile.id:
            raise ValueError(
                f"RuntimeContext audit profile_id "
                f"{self.audit.profile_id!r} does not match profile "
                f"{self.profile.id!r}."
            )

        if not self.registry.has_profile(self.profile.id):
            raise ValueError(
                f"RuntimeContext profile {self.profile.id!r} is not "
                "registered."
            )

        registered_profile = self.registry.get_profile(self.profile.id)

        if registered_profile != self.profile:
            raise ValueError(
                f"RuntimeContext profile {self.profile.id!r} does not match "
                "the profile stored in the registry."
            )

    def _validate_processor_results(self) -> None:
        """Validate preloaded processor results."""
        from uaaf_core.contracts.processor import ProcessorResult

        normalized_results: dict[str, ProcessorResult] = {}

        for processor_id, result in self.processor_results.items():
            normalized_id = self._normalize_identifier(
                value=processor_id,
                field_name="processor result key",
            )

            if not isinstance(result, ProcessorResult):
                raise TypeError(
                    "RuntimeContext processor_results must contain only "
                    "ProcessorResult instances, "
                    f"received {type(result).__name__}."
                )

            if normalized_id != result.processor_id:
                raise ValueError(
                    f"RuntimeContext processor result key {normalized_id!r} "
                    f"does not match result processor_id "
                    f"{result.processor_id!r}."
                )

            normalized_results[normalized_id] = result

        self.processor_results = normalized_results

    def _validate_metrics(self) -> None:
        """Validate preloaded runtime metrics."""
        normalized_metrics: dict[str, int | float] = {}

        for name, value in self.metrics.items():
            normalized_name = self._normalize_identifier(
                value=name,
                field_name="metric name",
            )

            normalized_metrics[normalized_name] = (
                self._normalize_metric_value(
                    value=value,
                    field_name=normalized_name,
                )
            )

        self.metrics = normalized_metrics

    @staticmethod
    def _validate_mapping(
        *,
        value: dict[str, Any],
        field_name: str,
    ) -> None:
        """Validate a required dictionary field."""
        if not isinstance(value, dict):
            raise TypeError(
                f"RuntimeContext {field_name} must be a dictionary, "
                f"received {type(value).__name__}."
            )

    @staticmethod
    def _normalize_identifier(
        *,
        value: str,
        field_name: str,
    ) -> str:
        """Validate and normalize a non-empty identifier."""
        if not isinstance(value, str):
            raise TypeError(
                f"RuntimeContext {field_name} must be a string, "
                f"received {type(value).__name__}."
            )

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(
                f"RuntimeContext {field_name} cannot be empty."
            )

        return normalized_value

    @staticmethod
    def _normalize_metric_value(
        *,
        value: int | float,
        field_name: str,
    ) -> int | float:
        """Validate a numeric runtime metric."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(
                f"RuntimeContext metric {field_name!r} must be numeric, "
                f"received {type(value).__name__}."
            )

        return value

    @staticmethod
    def _normalize_datetime(
        *,
        value: datetime,
        field_name: str,
    ) -> datetime:
        """Validate and normalize a timezone-aware datetime to UTC."""
        if not isinstance(value, datetime):
            raise TypeError(
                f"RuntimeContext {field_name} must be a datetime, "
                f"received {type(value).__name__}."
            )

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                f"RuntimeContext {field_name} must include "
                "timezone information."
            )

        return value.astimezone(UTC)