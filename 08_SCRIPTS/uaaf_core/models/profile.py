"""
Audit profile domain model for the Universal Architecture Audit Framework.

This module defines the canonical representation of a UAAF audit profile.
A profile declares which audit domains, processors, rule packages, plugins,
and configuration values participate in an audit execution.

Profile loading, schema validation, processor resolution, plugin discovery,
and pipeline construction are intentionally outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from uaaf_core.models.enums import AuditDomain, ComplianceLevel


@dataclass(frozen=True, slots=True)
class AuditProfile:
    """
    Represent a declarative UAAF audit profile.

    An AuditProfile defines the composition of an audit without executing any
    runtime behavior.

    Attributes:
        profile_id:
            Unique profile identifier.
        name:
            Human-readable profile name.
        version:
            Profile version.
        description:
            Human-readable profile purpose.
        compliance_level:
            UAAF compliance level targeted by the profile.
        domains:
            Audit domains included in the profile.
        processor_ids:
            Ordered processor identifiers used to build the pipeline.
        rule_package_ids:
            Rule package identifiers enabled by the profile.
        plugin_ids:
            Plugin identifiers required by the profile.
        configuration:
            Profile-specific configuration values.
        enabled:
            Whether the profile is available for execution.
    """

    profile_id: str
    name: str
    version: str
    description: str = ""
    compliance_level: ComplianceLevel = ComplianceLevel.CORE
    domains: tuple[AuditDomain, ...] = ()
    processor_ids: tuple[str, ...] = ()
    rule_package_ids: tuple[str, ...] = ()
    plugin_ids: tuple[str, ...] = ()
    configuration: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def __post_init__(self) -> None:
        """Normalize and validate the profile definition."""
        object.__setattr__(
            self,
            "profile_id",
            self._normalize_required_string(
                value=self.profile_id,
                field_name="profile_id",
            ),
        )

        object.__setattr__(
            self,
            "name",
            self._normalize_required_string(
                value=self.name,
                field_name="name",
            ),
        )

        object.__setattr__(
            self,
            "version",
            self._normalize_required_string(
                value=self.version,
                field_name="version",
            ),
        )

        object.__setattr__(
            self,
            "description",
            self._normalize_optional_string(
                value=self.description,
                field_name="description",
            ),
        )

        if not isinstance(self.compliance_level, ComplianceLevel):
            raise TypeError(
                "AuditProfile compliance_level must be a ComplianceLevel "
                f"instance, received {type(self.compliance_level).__name__}."
            )

        object.__setattr__(
            self,
            "domains",
            self._normalize_domains(self.domains),
        )

        object.__setattr__(
            self,
            "processor_ids",
            self._normalize_identifier_tuple(
                values=self.processor_ids,
                field_name="processor_ids",
            ),
        )

        object.__setattr__(
            self,
            "rule_package_ids",
            self._normalize_identifier_tuple(
                values=self.rule_package_ids,
                field_name="rule_package_ids",
            ),
        )

        object.__setattr__(
            self,
            "plugin_ids",
            self._normalize_identifier_tuple(
                values=self.plugin_ids,
                field_name="plugin_ids",
            ),
        )

        if not isinstance(self.configuration, dict):
            raise TypeError(
                "AuditProfile configuration must be a dictionary, "
                f"received {type(self.configuration).__name__}."
            )

        object.__setattr__(
            self,
            "configuration",
            dict(self.configuration),
        )

        if not isinstance(self.enabled, bool):
            raise TypeError(
                "AuditProfile enabled must be a boolean, "
                f"received {type(self.enabled).__name__}."
            )

    @property
    def id(self) -> str:
        """Return the canonical profile identifier."""
        return self.profile_id

    @property
    def is_executable(self) -> bool:
        """
        Return whether the profile has the minimum executable definition.

        A profile is executable when it is enabled and declares at least one
        processor.
        """
        return self.enabled and bool(self.processor_ids)

    @property
    def domain_count(self) -> int:
        """Return the number of audit domains configured."""
        return len(self.domains)

    @property
    def processor_count(self) -> int:
        """Return the number of configured processors."""
        return len(self.processor_ids)

    @property
    def rule_package_count(self) -> int:
        """Return the number of configured rule packages."""
        return len(self.rule_package_ids)

    @property
    def plugin_count(self) -> int:
        """Return the number of required plugins."""
        return len(self.plugin_ids)

    def includes_domain(self, domain: AuditDomain) -> bool:
        """
        Return whether the profile includes an audit domain.

        Args:
            domain:
                Audit domain to check.
        """
        if not isinstance(domain, AuditDomain):
            raise TypeError(
                "AuditProfile domain must be an AuditDomain instance, "
                f"received {type(domain).__name__}."
            )

        return domain in self.domains

    def requires_processor(self, processor_id: str) -> bool:
        """
        Return whether the profile requires a processor.

        Args:
            processor_id:
                Processor identifier to check.
        """
        normalized_id = self._normalize_required_string(
            value=processor_id,
            field_name="processor_id",
        )

        return normalized_id in self.processor_ids

    def requires_rule_package(self, rule_package_id: str) -> bool:
        """
        Return whether the profile requires a rule package.

        Args:
            rule_package_id:
                Rule package identifier to check.
        """
        normalized_id = self._normalize_required_string(
            value=rule_package_id,
            field_name="rule_package_id",
        )

        return normalized_id in self.rule_package_ids

    def requires_plugin(self, plugin_id: str) -> bool:
        """
        Return whether the profile requires a plugin.

        Args:
            plugin_id:
                Plugin identifier to check.
        """
        normalized_id = self._normalize_required_string(
            value=plugin_id,
            field_name="plugin_id",
        )

        return normalized_id in self.plugin_ids

    def get_configuration(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Return one profile configuration value.

        Args:
            key:
                Configuration key.
            default:
                Value returned when the key does not exist.
        """
        normalized_key = self._normalize_required_string(
            value=key,
            field_name="configuration key",
        )

        return self.configuration.get(normalized_key, default)

    def with_configuration(
        self,
        overrides: dict[str, Any],
    ) -> AuditProfile:
        """
        Return a new profile with configuration overrides applied.

        Args:
            overrides:
                Configuration values to merge into the current profile.

        Returns:
            A new immutable AuditProfile instance.
        """
        if not isinstance(overrides, dict):
            raise TypeError(
                "AuditProfile overrides must be a dictionary, "
                f"received {type(overrides).__name__}."
            )

        merged_configuration = {
            **self.configuration,
            **overrides,
        }

        return AuditProfile(
            profile_id=self.profile_id,
            name=self.name,
            version=self.version,
            description=self.description,
            compliance_level=self.compliance_level,
            domains=self.domains,
            processor_ids=self.processor_ids,
            rule_package_ids=self.rule_package_ids,
            plugin_ids=self.plugin_ids,
            configuration=merged_configuration,
            enabled=self.enabled,
        )

    @staticmethod
    def _normalize_required_string(
        *,
        value: str,
        field_name: str,
    ) -> str:
        """Validate and normalize a required string value."""
        if not isinstance(value, str):
            raise TypeError(
                f"AuditProfile {field_name} must be a string, "
                f"received {type(value).__name__}."
            )

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(
                f"AuditProfile {field_name} cannot be empty."
            )

        return normalized_value

    @staticmethod
    def _normalize_optional_string(
        *,
        value: str,
        field_name: str,
    ) -> str:
        """Validate and normalize an optional string value."""
        if not isinstance(value, str):
            raise TypeError(
                f"AuditProfile {field_name} must be a string, "
                f"received {type(value).__name__}."
            )

        return value.strip()

    @classmethod
    def _normalize_identifier_tuple(
        cls,
        *,
        values: tuple[str, ...],
        field_name: str,
    ) -> tuple[str, ...]:
        """Validate and normalize an ordered tuple of unique identifiers."""
        if not isinstance(values, tuple):
            raise TypeError(
                f"AuditProfile {field_name} must be a tuple, "
                f"received {type(values).__name__}."
            )

        normalized_values: list[str] = []

        for value in values:
            normalized_value = cls._normalize_required_string(
                value=value,
                field_name=f"{field_name} item",
            )

            if normalized_value in normalized_values:
                raise ValueError(
                    f"AuditProfile {field_name} contains duplicate value "
                    f"{normalized_value!r}."
                )

            normalized_values.append(normalized_value)

        return tuple(normalized_values)

    @staticmethod
    def _normalize_domains(
        values: tuple[AuditDomain, ...],
    ) -> tuple[AuditDomain, ...]:
        """Validate an ordered tuple of unique audit domains."""
        if not isinstance(values, tuple):
            raise TypeError(
                "AuditProfile domains must be a tuple, "
                f"received {type(values).__name__}."
            )

        normalized_values: list[AuditDomain] = []

        for value in values:
            if not isinstance(value, AuditDomain):
                raise TypeError(
                    "AuditProfile domains must contain only AuditDomain "
                    f"instances, received {type(value).__name__}."
                )

            if value in normalized_values:
                raise ValueError(
                    "AuditProfile domains contains duplicate value "
                    f"{value.value!r}."
                )

            normalized_values.append(value)

        return tuple(normalized_values)