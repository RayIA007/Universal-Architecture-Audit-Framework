"""
Central component and plugin registry for the Universal Architecture Audit Framework.

``UAAFRegistry`` preserves the original processor/profile registry contract and
adds the canonical registry for dynamically discovered auditor plugins.

The registry is responsible for:

- processor classes;
- audit profiles;
- deterministic plugin discovery and import;
- plugin validation, registration, lookup, listing, and selection.

The registry does not execute plugins, orchestrate audit sessions, or generate
reports.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from inspect import isabstract
from pathlib import Path
from threading import RLock
from types import MappingProxyType, ModuleType
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

from uaaf_core.contracts.processor import ProcessorContract
from uaaf_core.models.profile import AuditProfile


class RegistryError(RuntimeError):
    """Base exception for registry failures."""


class PluginDiscoveryError(RegistryError):
    """Base exception for plugin discovery and validation failures."""


class PluginDirectoryError(PluginDiscoveryError):
    """Raised when the configured framework or plugin directory is invalid."""


class NoPluginsDiscoveredError(PluginDiscoveryError):
    """Raised when discovery does not produce any valid auditor plugin."""


class PluginStructureError(PluginDiscoveryError):
    """Raised when a plugin candidate does not satisfy its file contract."""


class PluginImportError(PluginDiscoveryError):
    """Raised when a plugin module cannot be imported safely."""


class PluginRunCallableError(PluginDiscoveryError):
    """Raised when a plugin does not expose callable ``run(context)``."""


class PluginMetadataError(PluginDiscoveryError):
    """Raised when required plugin metadata is missing or invalid."""


class DuplicatePluginError(PluginDiscoveryError):
    """Raised when two different plugins declare the same plugin identifier."""


class DuplicatePluginAliasError(PluginDiscoveryError):
    """Raised when a selector alias resolves to more than one plugin."""


class PluginSelectionError(ValueError):
    """Base exception for invalid plugin selections."""


class UnknownPluginError(PluginSelectionError):
    """Raised when a requested plugin selector is not registered."""


@dataclass(frozen=True, slots=True)
class PluginDiscoveryIssue:
    """Non-fatal deterministic issue found while scanning plugin directories."""

    code: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class PluginDescriptor:
    """Canonical immutable representation of one validated auditor plugin.

    The first fields intentionally preserve the public descriptor contract that
    existed in ``uaaf_core.orchestrator`` before the dynamic registry phase.
    Additional fields provide stable registry metadata without requiring any
    new constants from the existing plugins.
    """

    name: str
    audit_type: str
    plugin_id: str
    plugin_version: str
    package_dir: Path
    module_path: Path
    runner: Callable[[dict[str, Any]], dict[str, Any]]
    module: ModuleType = field(repr=False, compare=False)
    allowed_context_fields: frozenset[str] = field(default_factory=frozenset)
    directory_name: str = ""
    relative_module_path: str = ""
    module_name: str = ""
    metadata: Mapping[str, Any] = field(
        default_factory=dict,
        repr=False,
        compare=False,
    )
    validation_status: str = "registered"

    def __post_init__(self) -> None:
        """Normalize compatibility defaults and freeze metadata."""
        directory_name = self.directory_name or self.package_dir.name or self.name
        relative_path = self.relative_module_path or self.module_path.as_posix()
        module_name = self.module_name or self.module.__name__

        object.__setattr__(self, "directory_name", directory_name)
        object.__setattr__(self, "relative_module_path", relative_path)
        object.__setattr__(self, "module_name", module_name)
        object.__setattr__(
            self,
            "allowed_context_fields",
            frozenset(self.allowed_context_fields),
        )
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )

    @property
    def aliases(self) -> frozenset[str]:
        """Return normalized, unambiguous selector candidates."""
        raw_aliases = {
            self.name,
            self.directory_name,
            self.audit_type,
            self.plugin_id,
            self.plugin_id.removesuffix("-auditor"),
        }
        return frozenset(
            _normalize_selector(alias)
            for alias in raw_aliases
            if isinstance(alias, str) and alias.strip()
        )

    @property
    def version(self) -> str:
        """Compatibility alias for ``plugin_version``."""
        return self.plugin_version

    @property
    def run(self) -> Callable[[dict[str, Any]], dict[str, Any]]:
        """Return the validated public plugin runner."""
        return self.runner

    @property
    def stable_path(self) -> str:
        """Return the stable POSIX path used in reports and errors."""
        return self.relative_module_path


@dataclass(frozen=True, slots=True)
class _ModuleCacheEntry:
    """Internal cache entry for deterministic repeated discovery."""

    signature: tuple[int, int, int, int]
    package_name: str
    module_name: str
    module: ModuleType
    owned_modules: tuple[tuple[str, ModuleType], ...]


class UAAFRegistry:
    """Store and resolve all components available to the UAAF runtime.

    Processor classes are stored instead of processor instances so every
    execution receives isolated mutable state. Profiles are immutable domain
    objects and may be stored directly. Auditor plugins are represented by
    validated :class:`PluginDescriptor` objects in deterministic order.
    """

    def __init__(
        self,
        *,
        framework_root: str | Path | None = None,
        plugins_dir: str | Path | None = None,
    ) -> None:
        """Initialize an empty thread-safe registry."""
        inferred_root = Path(__file__).resolve().parents[2]
        configured_root = Path(framework_root or inferred_root).expanduser()
        configured_plugins = Path(
            plugins_dir or configured_root / "plugins"
        ).expanduser()

        self._framework_root = configured_root
        self._plugins_dir = configured_plugins
        self._processor_types: dict[str, type[ProcessorContract]] = {}
        self._profiles: dict[str, AuditProfile] = {}
        self._plugins: dict[str, PluginDescriptor] = {}
        self._plugin_order: tuple[str, ...] = ()
        self._selector_index: dict[str, str] = {}
        self._discovery_issues: tuple[PluginDiscoveryIssue, ...] = ()
        self._module_cache: dict[Path, _ModuleCacheEntry] = {}
        self._lock = RLock()

    # ------------------------------------------------------------------
    # General state
    # ------------------------------------------------------------------

    @property
    def framework_root(self) -> Path:
        """Return the configured framework root without validating it."""
        return self._framework_root.expanduser().resolve()

    @property
    def plugins_dir(self) -> Path:
        """Return the configured plugin directory without validating it."""
        return self._plugins_dir.expanduser().resolve()

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
    def plugin_count(self) -> int:
        """Return the number of registered auditor plugins."""
        with self._lock:
            return len(self._plugins)

    @property
    def is_empty(self) -> bool:
        """Return whether the registry contains no components or plugins."""
        with self._lock:
            return (
                not self._processor_types
                and not self._profiles
                and not self._plugins
            )

    def __len__(self) -> int:
        """Return the number of registered auditor plugins."""
        return self.plugin_count

    def __iter__(self) -> Iterator[PluginDescriptor]:
        """Iterate over plugins in deterministic registry order."""
        return iter(self.list_plugins())

    # ------------------------------------------------------------------
    # Processor registry — preserved public contract
    # ------------------------------------------------------------------

    def register_processor(
        self,
        processor_type: type[ProcessorContract],
        *,
        replace: bool = False,
    ) -> None:
        """Register one concrete processor class."""
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
        """Remove one registered processor."""
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
        """Return whether a processor identifier is registered."""
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
        """Return the registered processor class."""
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

    def create_processor(self, processor_id: str) -> ProcessorContract:
        """Create a new isolated processor instance."""
        processor_type = self.get_processor_type(processor_id)
        try:
            return processor_type()
        except Exception as error:
            raise RuntimeError(
                f"Registered processor {processor_id!r} could not be "
                "instantiated."
            ) from error

    def list_processor_ids(self) -> tuple[str, ...]:
        """Return registered processor identifiers in deterministic order."""
        with self._lock:
            return tuple(sorted(self._processor_types))

    # ------------------------------------------------------------------
    # Profile registry — preserved public contract
    # ------------------------------------------------------------------

    def register_profile(
        self,
        profile: AuditProfile,
        *,
        replace: bool = False,
    ) -> None:
        """Register one audit profile."""
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
        """Remove one registered audit profile."""
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
        """Return whether an audit profile is registered."""
        normalized_id = self._normalize_identifier(
            value=profile_id,
            field_name="profile identifier",
        )
        with self._lock:
            return normalized_id in self._profiles

    def get_profile(self, profile_id: str) -> AuditProfile:
        """Return one registered audit profile."""
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
        """Return processor dependencies missing from a profile."""
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
        """Create the ordered processor sequence declared by a profile."""
        profile = self.get_profile(profile_id)
        if not profile.enabled:
            raise ValueError(f"Audit profile {profile.id!r} is disabled.")
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

    # ------------------------------------------------------------------
    # Canonical plugin registry
    # ------------------------------------------------------------------

    def discover_plugins(
        self,
        *,
        framework_root: str | Path | None = None,
        plugins_dir: str | Path | None = None,
    ) -> tuple[PluginDescriptor, ...]:
        """Discover, validate, import, and atomically register auditor plugins.

        Discovery is deterministic and idempotent for an unchanged directory.
        Incomplete package directories are skipped and exposed through
        :meth:`list_discovery_issues`; import, callable, metadata, duplicate-ID,
        and ambiguous-alias failures abort the transaction with a specific
        exception while preserving the previously registered plugin set.
        """
        configured_root = Path(framework_root or self._framework_root).expanduser()
        configured_plugins = Path(
            plugins_dir
            or (
                configured_root / "plugins"
                if framework_root is not None
                else self._plugins_dir
            )
        ).expanduser()

        root = self._require_directory(configured_root, "framework_root")
        directory = self._require_directory(configured_plugins, "plugins_dir")
        scripts_dir = root / "08_SCRIPTS"

        with self._lock:
            cache_snapshot = dict(self._module_cache)
            issues: list[PluginDiscoveryIssue] = []
            descriptors: list[PluginDescriptor] = []
            try:
                with _temporary_sys_path((root, scripts_dir)):
                    for package_dir in self._candidate_directories(directory):
                        try:
                            descriptor = self._discover_candidate(
                                root=root,
                                package_dir=package_dir,
                                issues=issues,
                            )
                        except PluginDiscoveryError as error:
                            issues.append(
                                PluginDiscoveryIssue(
                                    code=_plugin_issue_code(error),
                                    path=self._stable_path(package_dir, root),
                                    message=str(error),
                                )
                            )
                            raise
                        if descriptor is not None:
                            descriptors.append(descriptor)

                if not descriptors:
                    self._discovery_issues = tuple(issues)
                    raise NoPluginsDiscoveredError(
                        f"No auditor plugins were discovered in {directory}."
                    )

                plugins, order, selector_index = self._build_plugin_state(
                    descriptors
                )
            except Exception as error:
                if not isinstance(error, PluginDiscoveryError):
                    error = PluginDiscoveryError(str(error))
                if not issues:
                    issues.append(
                        PluginDiscoveryIssue(
                            code=_plugin_issue_code(error),
                            path=self._stable_path(directory, root),
                            message=str(error),
                        )
                    )
                self._rollback_module_cache(cache_snapshot)
                self._discovery_issues = tuple(issues)
                raise error

            self._framework_root = root
            self._plugins_dir = directory
            self._plugins = plugins
            self._plugin_order = order
            self._selector_index = selector_index
            self._discovery_issues = tuple(issues)
            self._discard_stale_modules(
                keep_paths={plugin.module_path.resolve() for plugin in descriptors}
            )
            return self.list_plugins()

    def register_plugin(
        self,
        plugin: PluginDescriptor,
        *,
        replace: bool = False,
    ) -> PluginDescriptor:
        """Register one validated plugin descriptor.

        Re-registering the same descriptor is a no-op. A different descriptor
        with the same ``plugin_id`` is rejected unless ``replace=True``.
        """
        if not isinstance(plugin, PluginDescriptor):
            raise TypeError(
                "Registry plugin must be a PluginDescriptor instance, "
                f"received {type(plugin).__name__}."
            )
        self._validate_descriptor(plugin)

        with self._lock:
            existing = self._plugins.get(plugin.plugin_id)
            if existing is plugin or existing == plugin:
                return existing
            if existing is not None and not replace:
                raise DuplicatePluginError(
                    "Duplicate plugin identifier "
                    f"{plugin.plugin_id!r}: {existing.stable_path!r} and "
                    f"{plugin.stable_path!r}."
                )

            candidates = [
                current
                for current in self.list_plugins()
                if current.plugin_id != plugin.plugin_id
            ]
            candidates.append(plugin)
            plugins, order, selector_index = self._build_plugin_state(candidates)
            self._plugins = plugins
            self._plugin_order = order
            self._selector_index = selector_index
            return plugin

    def unregister_plugin(self, plugin_id: str) -> None:
        """Remove one plugin by canonical ``plugin_id``."""
        normalized_id = self._normalize_identifier(
            value=plugin_id,
            field_name="plugin identifier",
        )
        with self._lock:
            if normalized_id not in self._plugins:
                raise KeyError(f"Plugin {normalized_id!r} is not registered.")
            remaining = [
                plugin
                for plugin in self.list_plugins()
                if plugin.plugin_id != normalized_id
            ]
            if remaining:
                plugins, order, selector_index = self._build_plugin_state(remaining)
            else:
                plugins, order, selector_index = {}, (), {}
            self._plugins = plugins
            self._plugin_order = order
            self._selector_index = selector_index

    def has_plugin(self, plugin_id: str) -> bool:
        """Return whether a canonical plugin identifier is registered."""
        normalized_id = self._normalize_identifier(
            value=plugin_id,
            field_name="plugin identifier",
        )
        with self._lock:
            return normalized_id in self._plugins

    def get_plugin(self, plugin_id: str) -> PluginDescriptor:
        """Return one plugin by canonical ``plugin_id``."""
        normalized_id = self._normalize_identifier(
            value=plugin_id,
            field_name="plugin identifier",
        )
        with self._lock:
            try:
                return self._plugins[normalized_id]
            except KeyError as error:
                raise KeyError(
                    f"Plugin {normalized_id!r} is not registered."
                ) from error

    def resolve_plugin(self, selector: str) -> PluginDescriptor:
        """Resolve one CLI-compatible selector to a registered plugin."""
        normalized = _normalize_selector(
            self._normalize_identifier(
                value=selector,
                field_name="plugin selector",
            )
        )
        with self._lock:
            plugin_id = self._selector_index.get(normalized)
            if plugin_id is None:
                available = ", ".join(
                    plugin.directory_name for plugin in self.list_plugins()
                )
                raise UnknownPluginError(
                    f"Unknown auditor selector {selector!r}. Available: {available}."
                )
            return self._plugins[plugin_id]

    def list_plugins(self) -> tuple[PluginDescriptor, ...]:
        """Return registered plugins in deterministic canonical order."""
        with self._lock:
            return tuple(self._plugins[plugin_id] for plugin_id in self._plugin_order)

    def list_plugin_ids(self) -> tuple[str, ...]:
        """Return canonical plugin identifiers in deterministic order."""
        with self._lock:
            return self._plugin_order

    def list_discovery_issues(self) -> tuple[PluginDiscoveryIssue, ...]:
        """Return non-fatal issues from the latest discovery attempt."""
        with self._lock:
            return self._discovery_issues

    def find_unknown_selectors(
        self,
        auditors: str | Sequence[str],
    ) -> tuple[str, ...]:
        """Return unknown normalized selectors without raising."""
        selectors = _split_csv(auditors)
        if not selectors or selectors == ["all"]:
            return ()
        if "all" in selectors:
            return tuple(selector for selector in selectors if selector != "all")
        normalized = _deduplicate(
            _normalize_selector(selector) for selector in selectors
        )
        with self._lock:
            return tuple(
                selector
                for selector in normalized
                if selector not in self._selector_index
            )

    def select_plugins(
        self,
        auditors: str | Sequence[str],
        *,
        reject_duplicate_selectors: bool = False,
    ) -> tuple[PluginDescriptor, ...]:
        """Select registered plugins using current CLI names and IDs.

        ``all`` and an empty selector return every plugin in canonical order.
        Explicit duplicate selectors are removed while preserving their first
        occurrence. The compatibility wrapper in ``orchestrator.py`` may opt
        into the legacy duplicate-rejection behavior.
        """
        selectors = _split_csv(auditors)
        if not selectors:
            return self.list_plugins()

        normalized = [_normalize_selector(selector) for selector in selectors]
        if reject_duplicate_selectors and len(normalized) != len(set(normalized)):
            raise PluginSelectionError(
                "Auditor selectors must not contain duplicates."
            )
        normalized = list(_deduplicate(normalized))

        if normalized == ["all"]:
            return self.list_plugins()
        if "all" in normalized:
            raise PluginSelectionError(
                "'all' cannot be combined with explicit auditor names."
            )

        with self._lock:
            unknown = [
                selector
                for selector in normalized
                if selector not in self._selector_index
            ]
            if unknown:
                available = ", ".join(
                    plugin.directory_name for plugin in self.list_plugins()
                )
                raise UnknownPluginError(
                    f"Unknown auditor selector(s): {unknown}. "
                    f"Available: {available}."
                )

            selected_ids = {
                self._selector_index[selector]
                for selector in normalized
            }
            return tuple(
                self._plugins[plugin_id]
                for plugin_id in self._plugin_order
                if plugin_id in selected_ids
            )

    # ------------------------------------------------------------------
    # Clearing and snapshots
    # ------------------------------------------------------------------

    def clear_processors(self) -> None:
        """Remove every registered processor type."""
        with self._lock:
            self._processor_types.clear()

    def clear_profiles(self) -> None:
        """Remove every registered audit profile."""
        with self._lock:
            self._profiles.clear()

    def clear_plugins(self) -> None:
        """Remove every plugin and dynamic import owned by this registry."""
        with self._lock:
            self._plugins.clear()
            self._plugin_order = ()
            self._selector_index.clear()
            self._discovery_issues = ()
            self._clear_module_cache()

    def clear(self) -> None:
        """Remove every component and plugin from the registry."""
        with self._lock:
            self._processor_types.clear()
            self._profiles.clear()
            self._plugins.clear()
            self._plugin_order = ()
            self._selector_index.clear()
            self._discovery_issues = ()
            self._clear_module_cache()

    def snapshot(self) -> dict[str, Any]:
        """Return the preserved processor/profile registry snapshot.

        The public shape intentionally remains identical to the pre-3.2
        contract so existing consumers that compare the dictionary exactly do
        not regress. Plugin state is exposed separately by
        :meth:`plugin_snapshot`.
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
                    "domains": [domain.value for domain in profile.domains],
                }
                for profile_id, profile in sorted(self._profiles.items())
            }
            return {
                "processor_count": len(processors),
                "profile_count": len(profiles),
                "processors": processors,
                "profiles": profiles,
            }

    def plugin_snapshot(self) -> dict[str, Any]:
        """Return a serializable deterministic summary of plugin state."""
        with self._lock:
            plugins = {
                plugin.plugin_id: {
                    "name": plugin.name,
                    "directory_name": plugin.directory_name,
                    "version": plugin.plugin_version,
                    "audit_type": plugin.audit_type,
                    "module": plugin.module_name,
                    "path": plugin.relative_module_path,
                    "validation_status": plugin.validation_status,
                }
                for plugin in self.list_plugins()
            }
            issues = [
                {
                    "code": issue.code,
                    "path": issue.path,
                    "message": issue.message,
                }
                for issue in self._discovery_issues
            ]
            return {
                "plugin_count": len(plugins),
                "plugins": plugins,
                "issues": issues,
            }

    # ------------------------------------------------------------------
    # Plugin discovery internals
    # ------------------------------------------------------------------

    @staticmethod
    def _candidate_directories(directory: Path) -> tuple[Path, ...]:
        """Return visible child directories in deterministic order."""
        return tuple(
            sorted(
                (
                    path
                    for path in directory.iterdir()
                    if path.is_dir()
                    and path.name != "__pycache__"
                    and not path.name.startswith(".")
                ),
                key=lambda path: (path.name.casefold(), path.name),
            )
        )

    def _discover_candidate(
        self,
        *,
        root: Path,
        package_dir: Path,
        issues: list[PluginDiscoveryIssue],
    ) -> PluginDescriptor | None:
        """Validate and import one candidate directory."""
        name = package_dir.name
        init_path = package_dir / "__init__.py"
        module_path = package_dir / f"{name}_auditor.py"

        missing: list[str] = []
        if not init_path.is_file():
            missing.append("__init__.py")
        if not module_path.is_file():
            missing.append(f"{name}_auditor.py")
        if missing:
            stable_package = self._stable_path(package_dir, root)
            issues.append(
                PluginDiscoveryIssue(
                    code="invalid_structure",
                    path=stable_package,
                    message=(
                        f"Plugin candidate {name!r} is missing required file(s): "
                        f"{', '.join(missing)}."
                    ),
                )
            )
            return None

        init_path = init_path.resolve()
        module_path = module_path.resolve()
        module = self._load_plugin_module(
            name=name,
            package_dir=package_dir.resolve(),
            init_path=init_path,
            module_path=module_path,
        )
        runner = getattr(module, "run", None)
        if not callable(runner):
            raise PluginRunCallableError(
                f"Plugin {name!r} must expose callable run(context)."
            )

        plugin_id = self._required_plugin_id(module, name)
        audit_type = self._optional_non_empty_string(
            getattr(module, "AUDIT_TYPE", name),
            field_name=f"{name}.AUDIT_TYPE",
        )
        plugin_version = self._optional_non_empty_string(
            getattr(module, "PLUGIN_VERSION", "1.0.0"),
            field_name=f"{name}.PLUGIN_VERSION",
        )
        canonical_name = self._optional_non_empty_string(
            getattr(module, "PLUGIN_NAME", name),
            field_name=f"{name}.PLUGIN_NAME",
        )
        allowed_fields = self._allowed_context_fields(module)
        relative_path = self._stable_path(module_path, root)
        metadata = self._plugin_metadata(module)

        descriptor = PluginDescriptor(
            name=canonical_name,
            directory_name=name,
            audit_type=audit_type,
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            package_dir=package_dir.resolve(),
            module_path=module_path,
            relative_module_path=relative_path,
            module_name=module.__name__,
            runner=runner,
            module=module,
            allowed_context_fields=allowed_fields,
            metadata=metadata,
        )
        self._validate_descriptor(descriptor)
        return descriptor

    def _load_plugin_module(
        self,
        *,
        name: str,
        package_dir: Path,
        init_path: Path,
        module_path: Path,
    ) -> ModuleType:
        """Import one plugin package with deterministic cache and cleanup.

        A collision-resistant package namespace preserves relative imports from
        sibling modules while preventing plugins from different roots from
        overwriting each other in ``sys.modules``.
        """
        try:
            init_stat = init_path.stat()
            module_stat = module_path.stat()
        except OSError as error:
            raise PluginImportError(
                f"Cannot inspect plugin module {module_path}: "
                f"{type(error).__name__}: {error}."
            ) from error

        signature = (
            init_stat.st_mtime_ns,
            init_stat.st_size,
            module_stat.st_mtime_ns,
            module_stat.st_size,
        )
        cached = self._module_cache.get(module_path)
        if cached is not None and cached.signature == signature:
            for owned_name, owned_module in cached.owned_modules:
                sys.modules[owned_name] = owned_module
            return cached.module

        package_name = _dynamic_package_name(name, package_dir)
        module_name = f"{package_name}.{name}_auditor"

        if cached is not None:
            self._remove_owned_modules(cached)

        existing_package = sys.modules.get(package_name)
        if existing_package is not None:
            existing_file = Path(
                getattr(existing_package, "__file__", "")
            ).resolve()
            if existing_file != init_path:
                raise PluginImportError(
                    f"Dynamic package name collision for plugin {name!r}: "
                    f"{package_name!r}."
                )
            self._remove_namespace(package_name)

        before_names = set(sys.modules)
        try:
            package_spec = importlib.util.spec_from_file_location(
                package_name,
                init_path,
                submodule_search_locations=[str(package_dir)],
            )
            if package_spec is None or package_spec.loader is None:
                raise PluginImportError(
                    f"Cannot create package import specification for {init_path}."
                )
            package_module = importlib.util.module_from_spec(package_spec)
            sys.modules[package_name] = package_module
            package_spec.loader.exec_module(package_module)

            imported_by_package = sys.modules.get(module_name)
            if imported_by_package is not None:
                imported_path = Path(
                    getattr(imported_by_package, "__file__", "")
                ).resolve()
                if imported_path != module_path:
                    raise PluginImportError(
                        f"Dynamic module name collision for plugin {name!r}: "
                        f"{module_name!r}."
                    )
                module = imported_by_package
            else:
                module_spec = importlib.util.spec_from_file_location(
                    module_name,
                    module_path,
                )
                if module_spec is None or module_spec.loader is None:
                    raise PluginImportError(
                        f"Cannot create import specification for {module_path}."
                    )
                module = importlib.util.module_from_spec(module_spec)
                sys.modules[module_name] = module
                module_spec.loader.exec_module(module)
        except PluginImportError:
            self._remove_namespace(package_name, before_names=before_names)
            raise
        except Exception as error:
            self._remove_namespace(package_name, before_names=before_names)
            message = str(error).strip()
            formatted = (
                f"{type(error).__name__}: {message}"
                if message
                else type(error).__name__
            )
            raise PluginImportError(
                f"Failed to import plugin {name!r} from {module_path}: "
                f"{formatted}."
            ) from error

        owned_modules = tuple(
            sorted(
                (
                    (owned_name, owned_module)
                    for owned_name, owned_module in sys.modules.items()
                    if (
                        owned_name == package_name
                        or owned_name.startswith(f"{package_name}.")
                    )
                    and isinstance(owned_module, ModuleType)
                ),
                key=lambda item: item[0],
            )
        )
        entry = _ModuleCacheEntry(
            signature=signature,
            package_name=package_name,
            module_name=module_name,
            module=module,
            owned_modules=owned_modules,
        )
        self._module_cache[module_path] = entry
        return module

    @staticmethod
    def _remove_namespace(
        package_name: str,
        *,
        before_names: set[str] | None = None,
    ) -> None:
        """Remove modules created under one dynamic package namespace."""
        for module_name in tuple(sys.modules):
            if module_name != package_name and not module_name.startswith(
                f"{package_name}."
            ):
                continue
            if before_names is not None and module_name in before_names:
                continue
            sys.modules.pop(module_name, None)

    @staticmethod
    def _remove_owned_modules(entry: _ModuleCacheEntry) -> None:
        """Remove cached modules only when their identities still match."""
        for module_name, module in reversed(entry.owned_modules):
            if sys.modules.get(module_name) is module:
                sys.modules.pop(module_name, None)

    def _build_plugin_state(
        self,
        descriptors: Iterable[PluginDescriptor],
    ) -> tuple[
        dict[str, PluginDescriptor],
        tuple[str, ...],
        dict[str, str],
    ]:
        """Validate descriptors and build deterministic indexes atomically."""
        ordered = sorted(
            descriptors,
            key=lambda plugin: (
                plugin.directory_name.casefold(),
                plugin.directory_name,
                plugin.plugin_id,
            ),
        )
        plugins: dict[str, PluginDescriptor] = {}
        for plugin in ordered:
            self._validate_descriptor(plugin)
            existing = plugins.get(plugin.plugin_id)
            if existing is not None and existing is not plugin:
                raise DuplicatePluginError(
                    "Duplicate plugin identifiers discovered: "
                    f"{[plugin.plugin_id]}. Paths: "
                    f"{existing.stable_path!r}, {plugin.stable_path!r}."
                )
            plugins[plugin.plugin_id] = plugin

        selector_index: dict[str, str] = {}
        for plugin in ordered:
            for alias in sorted(plugin.aliases):
                existing_id = selector_index.get(alias)
                if existing_id is not None and existing_id != plugin.plugin_id:
                    raise DuplicatePluginAliasError(
                        f"Ambiguous plugin selector {alias!r} resolves to "
                        f"{existing_id!r} and {plugin.plugin_id!r}."
                    )
                selector_index[alias] = plugin.plugin_id

        order = tuple(plugin.plugin_id for plugin in ordered)
        return plugins, order, selector_index

    @staticmethod
    def _validate_descriptor(plugin: PluginDescriptor) -> None:
        """Validate a canonical plugin descriptor."""
        for field_name, value in (
            ("name", plugin.name),
            ("directory_name", plugin.directory_name),
            ("audit_type", plugin.audit_type),
            ("plugin_id", plugin.plugin_id),
            ("plugin_version", plugin.plugin_version),
            ("module_name", plugin.module_name),
            ("relative_module_path", plugin.relative_module_path),
        ):
            if not isinstance(value, str) or not value.strip():
                raise PluginMetadataError(
                    f"Plugin descriptor {field_name} must be a non-empty string."
                )
        if not callable(plugin.runner):
            raise PluginRunCallableError(
                f"Plugin {plugin.directory_name!r} must expose callable run(context)."
            )
        if not isinstance(plugin.module, ModuleType):
            raise PluginMetadataError(
                f"Plugin {plugin.directory_name!r} module must be a ModuleType."
            )

    @staticmethod
    def _required_plugin_id(module: ModuleType, name: str) -> str:
        """Return and validate the required canonical plugin ID."""
        if not hasattr(module, "PLUGIN_ID"):
            raise PluginMetadataError(
                f"{name}.PLUGIN_ID must be defined as a non-empty string."
            )
        value = getattr(module, "PLUGIN_ID")
        if not isinstance(value, str) or not value.strip():
            raise PluginMetadataError(
                f"{name}.PLUGIN_ID must be a non-empty string."
            )
        return value.strip()

    @staticmethod
    def _optional_non_empty_string(value: Any, *, field_name: str) -> str:
        """Validate one present or defaulted metadata string."""
        if not isinstance(value, str) or not value.strip():
            raise PluginMetadataError(
                f"{field_name} must be a non-empty string."
            )
        return value.strip()

    @staticmethod
    def _allowed_context_fields(module: ModuleType) -> frozenset[str]:
        """Read optional context-field metadata without breaking old plugins."""
        raw = getattr(module, "_ALLOWED_CONTEXT_FIELDS", ())
        if not isinstance(raw, (set, frozenset, list, tuple)):
            return frozenset()
        return frozenset(
            item.strip()
            for item in raw
            if isinstance(item, str) and item.strip()
        )

    @staticmethod
    def _plugin_metadata(module: ModuleType) -> Mapping[str, Any]:
        """Collect relevant, safe module metadata."""
        keys = (
            "PLUGIN_ID",
            "PLUGIN_NAME",
            "PLUGIN_VERSION",
            "AUDIT_TYPE",
        )
        return {
            key: getattr(module, key)
            for key in keys
            if hasattr(module, key)
        }

    @staticmethod
    def _stable_path(path: Path, root: Path) -> str:
        """Return a deterministic POSIX path relative to the framework root."""
        resolved = path.resolve()
        try:
            return resolved.relative_to(root.resolve()).as_posix()
        except ValueError:
            return resolved.as_posix()

    @staticmethod
    def _require_directory(value: Path, field_name: str) -> Path:
        """Validate and resolve one required directory."""
        path = value.expanduser().resolve()
        if not path.exists():
            raise PluginDirectoryError(
                f"{field_name} does not exist: {path}."
            )
        if not path.is_dir():
            raise PluginDirectoryError(
                f"{field_name} is not a directory: {path}."
            )
        return path

    def _rollback_module_cache(
        self,
        snapshot: Mapping[Path, _ModuleCacheEntry],
    ) -> None:
        """Restore dynamic-module state after a failed discovery transaction."""
        current = dict(self._module_cache)
        for path, entry in current.items():
            previous = snapshot.get(path)
            if previous is entry:
                continue
            self._remove_owned_modules(entry)
        self._module_cache = dict(snapshot)
        for entry in snapshot.values():
            for module_name, module in entry.owned_modules:
                sys.modules[module_name] = module

    def _discard_stale_modules(self, *, keep_paths: set[Path]) -> None:
        """Remove cached modules no longer represented by discovered plugins."""
        for path in tuple(self._module_cache):
            if path in keep_paths:
                continue
            entry = self._module_cache.pop(path)
            self._remove_owned_modules(entry)

    def _clear_module_cache(self) -> None:
        """Remove every dynamic module owned by this registry."""
        for entry in self._module_cache.values():
            self._remove_owned_modules(entry)
        self._module_cache.clear()

    # ------------------------------------------------------------------
    # Existing shared validation helpers
    # ------------------------------------------------------------------

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
                "Registry processor_type must inherit from ProcessorContract."
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
    def _normalize_identifier(*, value: str, field_name: str) -> str:
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


@contextmanager
def _temporary_sys_path(paths: Iterable[Path]) -> Iterator[None]:
    """Temporarily prepend existing import roots and restore global state."""
    original = list(sys.path)
    try:
        for path in reversed(tuple(paths)):
            if path.is_dir():
                text = str(path)
                if text not in sys.path:
                    sys.path.insert(0, text)
        yield
    finally:
        sys.path[:] = original


def _dynamic_package_name(name: str, package_dir: Path) -> str:
    """Build a deterministic collision-resistant plugin package name."""
    safe_name = re.sub(r"[^A-Za-z0-9_]", "_", name)
    digest = hashlib.sha256(
        str(package_dir.resolve()).encode("utf-8")
    ).hexdigest()[:16]
    return f"_uaaf_plugin_{safe_name}_{digest}"



def _plugin_issue_code(error: PluginDiscoveryError) -> str:
    """Map one registry exception to a stable discovery issue code."""
    if isinstance(error, PluginImportError):
        return "import_error"
    if isinstance(error, PluginRunCallableError):
        return "invalid_run_callable"
    if isinstance(error, PluginMetadataError):
        return "invalid_metadata"
    if isinstance(error, (DuplicatePluginError, DuplicatePluginAliasError)):
        return "duplicate_plugin"
    if isinstance(error, PluginDirectoryError):
        return "invalid_directory"
    if isinstance(error, NoPluginsDiscoveredError):
        return "no_plugins_discovered"
    return "plugin_discovery_error"

def _normalize_selector(value: str) -> str:
    """Normalize CLI selector spelling without creating broad aliases."""
    return value.strip().casefold().replace("_", "-")


def _split_csv(value: Any) -> list[str]:
    """Split a string or sequence of comma-separated strings."""
    if value is None:
        return []
    raw_items = [value] if isinstance(value, str) else list(value)
    items: list[str] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, str):
            raise TypeError("Comma-separated values must contain strings.")
        items.extend(
            part.strip().casefold()
            for part in raw_item.split(",")
            if part.strip()
        )
    return items


def _deduplicate(values: Iterable[str]) -> tuple[str, ...]:
    """Remove duplicates while preserving first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


__all__ = [
    "DuplicatePluginAliasError",
    "DuplicatePluginError",
    "NoPluginsDiscoveredError",
    "PluginDescriptor",
    "PluginDirectoryError",
    "PluginDiscoveryError",
    "PluginDiscoveryIssue",
    "PluginImportError",
    "PluginMetadataError",
    "PluginRunCallableError",
    "PluginSelectionError",
    "PluginStructureError",
    "RegistryError",
    "UAAFRegistry",
    "UnknownPluginError",
]
