"""
Domain enumerations for the Universal Architecture Audit Framework.

This module contains the canonical enumerated values used by UAAF domain
models. Enumerations defined here must remain independent from runtime,
storage, reporting, and plugin implementations.
"""

from __future__ import annotations

from enum import Enum
from typing import Self


class DomainEnum(str, Enum):
    """
    Base class for string-based domain enumerations.

    DomainEnum provides predictable string serialization while preserving
    strict enumeration semantics.
    """

    def __str__(self) -> str:
        """Return the serialized value of the enumeration member."""
        return self.value

    @classmethod
    def from_value(cls, value: str) -> Self:
        """
        Resolve an enumeration member from a string value.

        Leading and trailing whitespace is ignored. Matching is
        case-insensitive.

        Args:
            value: Raw string value to resolve.

        Returns:
            The matching enumeration member.

        Raises:
            TypeError: If value is not a string.
            ValueError: If value does not match a supported member.
        """
        if not isinstance(value, str):
            raise TypeError(
                f"{cls.__name__}.from_value() requires a string, "
                f"received {type(value).__name__}."
            )

        normalized_value = value.strip().lower()

        for member in cls:
            if member.value.lower() == normalized_value:
                return member

        supported_values = ", ".join(member.value for member in cls)

        raise ValueError(
            f"Unsupported {cls.__name__} value: {value!r}. "
            f"Supported values: {supported_values}."
        )


class AuditStatus(DomainEnum):
    """Lifecycle status of an audit."""

    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SessionStatus(DomainEnum):
    """Lifecycle status of an audit session."""

    CREATED = "created"
    OPEN = "open"
    RUNNING = "running"
    CLOSING = "closing"
    CLOSED = "closed"
    FAILED = "failed"


class ProcessorStatus(DomainEnum):
    """Execution status of a pipeline processor."""

    CREATED = "created"
    REGISTERED = "registered"
    PENDING = "pending"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"
    FINALIZED = "finalized"


class FindingStatus(DomainEnum):
    """Resolution status of an audit finding."""

    OPEN = "open"
    CONFIRMED = "confirmed"
    ACCEPTED = "accepted"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    SUPPRESSED = "suppressed"


class Severity(DomainEnum):
    """Impact severity assigned to a finding."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceType(DomainEnum):
    """Classification of evidence collected during an audit."""

    FILE = "file"
    DIRECTORY = "directory"
    TEXT_EXTRACT = "text_extract"
    CODE_EXTRACT = "code_extract"
    CONFIGURATION = "configuration"
    METADATA = "metadata"
    OBSERVATION = "observation"
    METRIC = "metric"


class ArtifactType(DomainEnum):
    """Classification of an artifact included in an audit target."""

    PROJECT = "project"
    DIRECTORY = "directory"
    FILE = "file"
    DOCUMENT = "document"
    SOURCE_CODE = "source_code"
    CONFIGURATION = "configuration"
    TEST = "test"
    SCHEMA = "schema"
    TEMPLATE = "template"
    UNKNOWN = "unknown"


class RuleStatus(DomainEnum):
    """Operational status of an audit rule."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class RuleResult(DomainEnum):
    """Evaluation result produced by an audit rule."""

    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"
    NOT_EVALUATED = "not_evaluated"
    ERROR = "error"


class ScoreType(DomainEnum):
    """Classification of an audit score."""

    RULE = "rule"
    DOMAIN = "domain"
    PROFILE = "profile"
    OVERALL = "overall"


class ReportType(DomainEnum):
    """Semantic type of an audit report."""

    MASTER_AUDIT_MATRIX = "master_audit_matrix"
    TECHNICAL = "technical"
    EXECUTIVE = "executive"
    EXECUTION_SUMMARY = "execution_summary"


class ReportFormat(DomainEnum):
    """Supported report serialization format."""

    MARKDOWN = "markdown"
    JSON = "json"


class PluginStatus(DomainEnum):
    """Lifecycle status of a UAAF plugin."""

    DISCOVERED = "discovered"
    REGISTERED = "registered"
    VALIDATED = "validated"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    FAILED = "failed"
    DISPOSED = "disposed"


class ComplianceLevel(DomainEnum):
    """Official UAAF framework compliance level."""

    CORE = "core"
    STANDARD = "standard"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class AuditDomain(DomainEnum):
    """Initial domains supported by UAAF v1.0."""

    GOVERNANCE = "governance"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    PYTHON_CODE = "python_code"
    TESTING = "testing"
    CONFIGURATION = "configuration"
    GENERAL = "general"