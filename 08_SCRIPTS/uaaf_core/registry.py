"""
Central component registry for the Universal Architecture Audit Framework.

The registry stores the components available to the UAAF runtime and provides
validated resolution methods.

This initial implementation manages:

- Processor classes
- Audit profiles
- Profile-to-processor resolution

The Registry does not execute processors, control sessions, build reports, or
perform audit orchestration.
"""

from __future__ import annotations

from inspect import isabstract
from threading import RLock
from typing import Any

from uaaf_core.contracts.processor import ProcessorContract
from uaaf_core.models.profile import AuditProfile


class UAAFRegistry:
    """
    Store and resolve components available to the UAAF runtime.

    Processor classes are registered instead of processor instances. This
    ensures that every execution receives an isolated processor object with
    clean mutable state.

    Profiles are immutable domain objects and may therefore be stored directly.
    """

    def __init__(self) -> None:
        """Initialize an empty thread-safe registry."""
        self._processor_types: dict[str, type[ProcessorContract]] = {}
        self._profiles: dict[str, AuditProfile] = {}
        self._lock = RLock()

    @property
    def processor_count(self) -> int:
        """Return the number of registered processor types."""
        with self._lock:
            return len(self._processor_types)

    @property
    def profile_count(self) -> int:
        """Return the number of registered audit profiles."""
        with self._lock:
            return len(self._profiles)

    @property
    def is_empty(self) -> bool:
        """Return whether the registry contains no components."""
        with self._lock:
            return not self._processor_types and not self._profiles

    def register_processor(
        self,
        processor_type: type[ProcessorContract],
        *,
        replace: bool = False,
    ) -> None:
        """
        Register one concrete processor class.

        Args:
            processor_type:
                Concrete subclass of ProcessorContract.
            replace:
                Whether an existing processor with the same identifier may be
                replaced.

        Raises:
            TypeError:
                If processor_type is not a ProcessorContract subclass.
            ValueError:
                If the processor is abstract, cannot be instantiated, or its
                identifier is already registered.
        """
        processor_type = self._validate_processor_type(processor_type)

        try:
            processor = processor_type()
        except Exception as error:
            raise ValueError(
                f"Processor type {processor_type.__name__!r} could not be "
                "instantiated without arguments."
            ) from error

        processor_id = self._normalize_identifier(
            value=processor.id,
            field_name="processor identifier",
        )

        with self._lock:
            if processor_id in self._processor_types and not replace:
                raise ValueError(
                    f"Processor {processor_id!r} is already registered."
                )

            self._processor_types[processor_id] = processor_type

    def unregister_processor(self, processor_id: str) -> None:
        """
        Remove one registered processor.

        Args:
            processor_id:
                Processor identifier.

        Raises:
            KeyError:
                If the processor is not registered.
        """
        normalized_id = self._normalize_identifier(
            value=processor_id,
            field_name="processor identifier",
        )

        with self._lock:
            if normalized_id not in self._processor_types:
                raise KeyError(
                    f"Processor {normalized_id!r} is not registered."
                )

            del self._processor_types[normalized_id]

    def has_processor(self, processor_id: str) -> bool:
        """
        Return whether a processor identifier is registered.

        Args:
            processor_id:
                Processor identifier.
        """
        normalized_id = self._normalize_identifier(
            value=processor_id,
            field_name="processor identifier",
        )

        with self._lock:
            return normalized_id in self._processor_types

    def get_processor_type(
        self,
        processor_id: str,
    ) -> type[ProcessorContract]:
        """
        Return the registered processor class.

        Args:
            processor_id:
                Processor identifier.

        Raises:
            KeyError:
                If the processor is not registered.
        """
        normalized_id = self._normalize_identifier(
            value=processor_id,
            field_name="processor identifier",
        )

        with self._lock:
            try:
                return self._processor_types[normalized_id]
            except KeyError as error:
                raise KeyError(
                    f"Processor {normalized_id!r} is not registered."
                ) from error

    def create_processor(
        self,
        processor_id: str,
    ) -> ProcessorContract:
        """
        Create a new isolated processor instance.

        Args:
            processor_id:
                Registered processor identifier.

        Returns:
            New ProcessorContract instance.

        Raises:
            KeyError:
                If the processor is not registered.
            RuntimeError:
                If the registered processor can no longer be instantiated.
        """
        processor_type = self.get_processor_type(processor_id)

        try:
            return processor_type()
        except Exception as error:
            raise RuntimeError(
                f"Registered processor {processor_id!r} could not be "
                "instantiated."
            ) from error

    def list_processor_ids(self) -> tuple[str, ...]:
        """
        Return registered processor identifiers in deterministic order.
        """
        with self._lock:
            return tuple(sorted(self._processor_types))

    def register_profile(
        self,
        profile: AuditProfile,
        *,
        replace: bool = False,
    ) -> None:
        """
        Register one audit profile.

        Args:
            profile:
                AuditProfile instance.
            replace:
                Whether an existing profile with the same identifier may be
                replaced.

        Raises:
            TypeError:
                If profile is not an AuditProfile.
            ValueError:
                If its identifier is already registered.
        """
        if not isinstance(profile, AuditProfile):
            raise TypeError(
                "Registry profile must be an AuditProfile instance, "
                f"received {type(profile).__name__}."
            )

        profile_id = self._normalize_identifier(
            value=profile.id,
            field_name="profile identifier",
        )

        with self._lock:
            if profile_id in self._profiles and not replace:
                raise ValueError(
                    f"Audit profile {profile_id!r} is already registered."
                )

            self._profiles[profile_id] = profile

    def unregister_profile(self, profile_id: str) -> None:
        """
        Remove one registered audit profile.

        Args:
            profile_id:
                Audit profile identifier.

        Raises:
            KeyError:
                If the profile is not registered.
        """
        normalized_id = self._normalize_identifier(
            value=profile_id,
            field_name="profile identifier",
        )

        with self._lock:
            if normalized_id not in self._profiles:
                raise KeyError(
                    f"Audit profile {normalized_id!r} is not registered."
                )

            del self._profiles[normalized_id]

    def has_profile(self, profile_id: str) -> bool:
        """
        Return whether an audit profile is registered.

        Args:
            profile_id:
                Audit profile identifier.
        """
        normalized_id = self._normalize_identifier(
            value=profile_id,
            field_name="profile identifier",
        )

        with self._lock:
            return normalized_id in self._profiles

    def get_profile(self, profile_id: str) -> AuditProfile:
        """
        Return one registered audit profile.

        Args:
            profile_id:
                Audit profile identifier.

        Raises:
            KeyError:
                If the profile is not registered.
        """
        normalized_id = self._normalize_identifier(
            value=profile_id,
            field_name="profile identifier",
        )

        with self._lock:
            try:
                return self._profiles[normalized_id]
            except KeyError as error:
                raise KeyError(
                    f"Audit profile {normalized_id!r} is not registered."
                ) from error

    def list_profile_ids(self) -> tuple[str, ...]:
        """Return registered profile identifiers in deterministic order."""
        with self._lock:
            return tuple(sorted(self._profiles))

    def validate_profile_dependencies(
        self,
        profile_id: str,
    ) -> tuple[str, ...]:
        """
        Return processor dependencies missing from a profile.

        Args:
            profile_id:
                Registered audit profile identifier.

        Returns:
            Ordered tuple containing processor identifiers that are required
            by the profile but are not registered.
        """
        profile = self.get_profile(profile_id)

        with self._lock:
            return tuple(
                processor_id
                for processor_id in profile.processor_ids
                if processor_id not in self._processor_types
            )

    def resolve_profile_processors(
        self,
        profile_id: str,
    ) -> tuple[ProcessorContract, ...]:
        """
        Create the ordered processor sequence declared by a profile.

        Args:
            profile_id:
                Registered audit profile identifier.

        Returns:
            Tuple of newly created processor instances in profile order.

        Raises:
            ValueError:
                If the profile is disabled or has missing processor
                dependencies.
        """
        profile = self.get_profile(profile_id)

        if not profile.enabled:
            raise ValueError(
                f"Audit profile {profile.id!r} is disabled."
            )

        if not profile.processor_ids:
            raise ValueError(
                f"Audit profile {profile.id!r} does not declare processors."
            )

        missing_processors = self.validate_profile_dependencies(profile.id)

        if missing_processors:
            missing = ", ".join(
                repr(processor_id)
                for processor_id in missing_processors
            )

            raise ValueError(
                f"Audit profile {profile.id!r} has unregistered processor "
                f"dependencies: {missing}."
            )

        return tuple(
            self.create_processor(processor_id)
            for processor_id in profile.processor_ids
        )

    def clear_processors(self) -> None:
        """Remove every registered processor type."""
        with self._lock:
            self._processor_types.clear()

    def clear_profiles(self) -> None:
        """Remove every registered audit profile."""
        with self._lock:
            self._profiles.clear()

    def clear(self) -> None:
        """Remove every component from the registry."""
        with self._lock:
            self._processor_types.clear()
            self._profiles.clear()

    def snapshot(self) -> dict[str, Any]:
        """
        Return a serializable summary of the current registry state.

        The snapshot contains component metadata only. It does not expose
        internal mutable dictionaries or processor instances.
        """
        with self._lock:
            processors = {
                processor_id: {
                    "class_name": processor_type.__name__,
                    "module": processor_type.__module__,
                    "version": processor_type.processor_version,
                    "description": processor_type.processor_description,
                }
                for processor_id, processor_type
                in sorted(self._processor_types.items())
            }

            profiles = {
                profile_id: {
                    "name": profile.name,
                    "version": profile.version,
                    "enabled": profile.enabled,
                    "processors": list(profile.processor_ids),
                    "domains": [
                        domain.value
                        for domain in profile.domains
                    ],
                }
                for profile_id, profile
                in sorted(self._profiles.items())
            }

            return {
                "processor_count": len(processors),
                "profile_count": len(profiles),
                "processors": processors,
                "profiles": profiles,
            }

    @staticmethod
    def _validate_processor_type(
        processor_type: type[ProcessorContract],
    ) -> type[ProcessorContract]:
        """Validate a concrete ProcessorContract subclass."""
        if not isinstance(processor_type, type):
            raise TypeError(
                "Registry processor_type must be a class, "
                f"received {type(processor_type).__name__}."
            )

        if not issubclass(processor_type, ProcessorContract):
            raise TypeError(
                "Registry processor_type must inherit from "
                "ProcessorContract."
            )

        if processor_type is ProcessorContract:
            raise ValueError(
                "ProcessorContract cannot be registered directly."
            )

        if isabstract(processor_type):
            raise ValueError(
                f"Processor type {processor_type.__name__!r} is abstract "
                "and cannot be registered."
            )

        return processor_type

    @staticmethod
    def _normalize_identifier(
        *,
        value: str,
        field_name: str,
    ) -> str:
        """Validate and normalize a registry identifier."""
        if not isinstance(value, str):
            raise TypeError(
                f"Registry {field_name} must be a string, "
                f"received {type(value).__name__}."
            )

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(
                f"Registry {field_name} cannot be empty."
            )

        return normalized_value