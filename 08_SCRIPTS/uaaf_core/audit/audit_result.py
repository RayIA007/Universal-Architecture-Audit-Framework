"""
Canonical audit-result contract for all UAAF auditors.

Every auditor must return a serializable dictionary produced from
AuditResult or validated by validate_audit_result().
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping


class AuditStatus(str, Enum):
    """Canonical lifecycle states for an audit execution."""

    COMPLETED = "completed"
    COMPLETED_WITH_FINDINGS = "completed_with_findings"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class FindingSeverity(str, Enum):
    """Canonical severity levels for audit findings."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class AuditFinding:
    """One normalized, actionable audit finding."""

    code: str
    severity: FindingSeverity
    path: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["severity"] = self.severity.value
        return payload


@dataclass(frozen=True, slots=True)
class AuditExecution:
    """Execution metadata shared by every auditor."""

    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AuditResult:
    """Canonical result returned by every UAAF auditor."""

    plugin_id: str
    plugin_version: str
    audit_type: str
    status: AuditStatus
    summary: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    findings: tuple[AuditFinding, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    execution: AuditExecution = field(default_factory=AuditExecution)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "plugin_id": self.plugin_id,
            "plugin_version": self.plugin_version,
            "audit_type": self.audit_type,
            "status": self.status.value,
            "summary": dict(self.summary),
            "metrics": dict(self.metrics),
            "findings": [
                finding.to_dict()
                for finding in self.findings
            ],
            "errors": list(self.errors),
            "execution": self.execution.to_dict(),
        }

        validate_audit_result(payload)
        return payload


def validate_audit_result(
    result: Mapping[str, Any],
) -> None:
    """Validate a dictionary against the canonical audit-result contract."""
    if not isinstance(result, Mapping):
        raise TypeError("Audit result must be a mapping.")

    required_keys = {
        "plugin_id",
        "plugin_version",
        "audit_type",
        "status",
        "summary",
        "metrics",
        "findings",
        "errors",
        "execution",
    }

    actual_keys = set(result)
    missing_keys = required_keys - actual_keys
    unexpected_keys = actual_keys - required_keys

    if missing_keys:
        raise ValueError(
            "Audit result is missing required keys: "
            f"{sorted(missing_keys)}"
        )

    if unexpected_keys:
        raise ValueError(
            "Audit result contains unexpected keys: "
            f"{sorted(unexpected_keys)}"
        )

    _require_non_empty_string(result["plugin_id"], "plugin_id")
    _require_non_empty_string(
        result["plugin_version"],
        "plugin_version",
    )
    _require_non_empty_string(result["audit_type"], "audit_type")

    valid_statuses = {status.value for status in AuditStatus}
    if result["status"] not in valid_statuses:
        raise ValueError(
            "Invalid audit status: "
            f"{result['status']!r}. "
            f"Expected one of {sorted(valid_statuses)}."
        )

    if not isinstance(result["summary"], Mapping):
        raise TypeError("summary must be a mapping.")

    if not isinstance(result["metrics"], Mapping):
        raise TypeError("metrics must be a mapping.")

    _validate_findings(result["findings"])
    _validate_errors(result["errors"])
    _validate_execution(result["execution"])


def _validate_findings(findings: Any) -> None:
    if not isinstance(findings, list):
        raise TypeError("findings must be a list.")

    valid_severities = {
        severity.value
        for severity in FindingSeverity
    }

    required_keys = {
        "code",
        "severity",
        "path",
        "message",
        "details",
    }

    for index, finding in enumerate(findings):
        if not isinstance(finding, Mapping):
            raise TypeError(
                f"findings[{index}] must be a mapping."
            )

        actual_keys = set(finding)

        if actual_keys != required_keys:
            raise ValueError(
                f"findings[{index}] must contain exactly "
                f"{sorted(required_keys)}."
            )

        _require_non_empty_string(
            finding["code"],
            f"findings[{index}].code",
        )
        _require_non_empty_string(
            finding["path"],
            f"findings[{index}].path",
        )
        _require_non_empty_string(
            finding["message"],
            f"findings[{index}].message",
        )

        if finding["severity"] not in valid_severities:
            raise ValueError(
                f"Invalid findings[{index}].severity: "
                f"{finding['severity']!r}."
            )

        if not isinstance(finding["details"], Mapping):
            raise TypeError(
                f"findings[{index}].details must be a mapping."
            )


def _validate_errors(errors: Any) -> None:
    if not isinstance(errors, list):
        raise TypeError("errors must be a list.")

    for index, error in enumerate(errors):
        _require_non_empty_string(
            error,
            f"errors[{index}]",
        )


def _validate_execution(execution: Any) -> None:
    if not isinstance(execution, Mapping):
        raise TypeError("execution must be a mapping.")

    required_keys = {
        "started_at",
        "completed_at",
        "duration_ms",
    }

    if set(execution) != required_keys:
        raise ValueError(
            "execution must contain exactly "
            f"{sorted(required_keys)}."
        )

    for key in ("started_at", "completed_at"):
        value = execution[key]
        if value is not None and not isinstance(value, str):
            raise TypeError(
                f"execution.{key} must be a string or None."
            )

    duration_ms = execution["duration_ms"]
    if (
        duration_ms is not None
        and (
            not isinstance(duration_ms, int)
            or isinstance(duration_ms, bool)
            or duration_ms < 0
        )
    ):
        raise ValueError(
            "execution.duration_ms must be a non-negative "
            "integer or None."
        )


def _require_non_empty_string(
    value: Any,
    field_name: str,
) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{field_name} must be a non-empty string."
        )


__all__ = [
    "AuditExecution",
    "AuditFinding",
    "AuditResult",
    "AuditStatus",
    "FindingSeverity",
    "validate_audit_result",
]
