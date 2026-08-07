"""Canonical global configuration for UAAF executions.

This module owns the deterministic interpretation of framework defaults,
configuration files, and explicit command-line overrides.  It intentionally
contains no plugin discovery logic; plugin names and aliases remain the
responsibility of :class:`uaaf_core.registry.UAAFRegistry`.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, fields
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

DEFAULT_AUDITORS: Final[tuple[str, ...]] = ("all",)
DEFAULT_OUTPUT_FORMATS: Final[tuple[str, ...]] = ("markdown", "json")
DEFAULT_FAIL_ON: Final[tuple[str, ...]] = ()
DEFAULT_EXCLUSIONS: Final[tuple[str, ...]] = ()
VALID_OUTPUT_FORMATS: Final[frozenset[str]] = frozenset(
    {"markdown", "json", "sarif"}
)
VALID_SEVERITIES: Final[frozenset[str]] = frozenset(
    {"critical", "error", "warning", "info"}
)
SUPPORTED_CONFIG_SUFFIXES: Final[frozenset[str]] = frozenset(
    {".json", ".toml", ".yaml", ".yml"}
)

_CLI_OPTION_TO_FIELD: Final[dict[str, str]] = {
    "--project-path": "project_path",
    "--auditors": "auditors",
    "--output-formats": "output_formats",
    "--config": "config",
    "--fail-on": "fail_on",
    "--exclude": "exclude",
    "--output-dir": "output_dir",
    "--plugins-dir": "plugins_dir",
    "--framework-root": "framework_root",
}

_GLOBAL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "project_path",
        "auditors",
        "output_formats",
        "fail_on",
        "exclude",
        "ignored_directories",
        "output_dir",
        "plugins_dir",
        "framework_root",
        "defaults",
        "global",
        "plugins",
    }
)

_SENSITIVE_KEY_PARTS: Final[tuple[str, ...]] = (
    "api_key",
    "apikey",
    "credential",
    "password",
    "secret",
    "token",
)


class GlobalConfigError(ValueError):
    """Base exception for expected global-configuration failures."""


class ConfigFileError(GlobalConfigError):
    """Raised when a configuration file cannot be loaded safely."""


class ConfigValidationError(GlobalConfigError):
    """Raised when configuration structure, types, or values are invalid."""


class ConfigConflictError(ConfigValidationError):
    """Raised when two aliases provide incompatible values."""


class _UnsetType:
    __slots__ = ()

    def __repr__(self) -> str:
        return "UNSET"


UNSET: Final[_UnsetType] = _UnsetType()


@dataclass(frozen=True, slots=True)
class ConfigOverrides:
    """Partial values from one source before precedence is applied."""

    project_path: Any = UNSET
    auditors: Any = UNSET
    output_formats: Any = UNSET
    fail_on: Any = UNSET
    exclude: Any = UNSET
    output_dir: Any = UNSET
    plugins_dir: Any = UNSET
    framework_root: Any = UNSET
    plugin_defaults: Any = UNSET
    plugin_configs: Any = UNSET

    def supplied_fields(self) -> tuple[str, ...]:
        """Return supplied field names in deterministic dataclass order."""
        return tuple(
            field.name
            for field in fields(self)
            if getattr(self, field.name) is not UNSET
        )


@dataclass(frozen=True, slots=True)
class LoadedConfig:
    """One parsed configuration file and its canonical absolute path."""

    path: Path | None
    data: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ResolvedConfig:
    """Immutable, validated configuration for one UAAF execution."""

    project_path: Path
    auditors: tuple[str, ...]
    output_formats: tuple[str, ...]
    config_path: Path | None
    fail_on: tuple[str, ...]
    exclude: tuple[str, ...]
    output_dir: Path
    plugins_dir: Path
    framework_root: Path
    plugin_defaults: Mapping[str, Any]
    plugin_configs: Mapping[str, Mapping[str, Any]]

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_path", self.project_path.resolve())
        object.__setattr__(self, "output_dir", self.output_dir.resolve())
        object.__setattr__(self, "plugins_dir", self.plugins_dir.resolve())
        object.__setattr__(self, "framework_root", self.framework_root.resolve())
        if self.config_path is not None:
            object.__setattr__(self, "config_path", self.config_path.resolve())
        object.__setattr__(self, "auditors", tuple(self.auditors))
        object.__setattr__(self, "output_formats", tuple(self.output_formats))
        object.__setattr__(self, "fail_on", tuple(self.fail_on))
        object.__setattr__(self, "exclude", tuple(self.exclude))
        object.__setattr__(
            self,
            "plugin_defaults",
            _freeze_mapping(self.plugin_defaults),
        )
        object.__setattr__(
            self,
            "plugin_configs",
            _freeze_plugin_configs(self.plugin_configs),
        )

    def plugin_source_mapping(self) -> dict[str, Any]:
        """Return a defensive legacy-shaped mapping for context projection."""
        return {
            "defaults": _thaw(self.plugin_defaults),
            "plugins": _thaw(self.plugin_configs),
        }

    def to_dict(self, *, redact_sensitive: bool = True) -> dict[str, Any]:
        """Return a deterministic and optionally redacted diagnostic snapshot."""
        snapshot: dict[str, Any] = {
            "project_path": str(self.project_path),
            "auditors": list(self.auditors),
            "output_formats": list(self.output_formats),
            "config_path": (
                str(self.config_path) if self.config_path is not None else None
            ),
            "fail_on": list(self.fail_on),
            "exclude": list(self.exclude),
            "output_dir": str(self.output_dir),
            "plugins_dir": str(self.plugins_dir),
            "framework_root": str(self.framework_root),
            "plugin_defaults": _ordered_plain(self.plugin_defaults),
            "plugin_configs": _ordered_plain(self.plugin_configs),
        }
        return _redact(snapshot) if redact_sensitive else snapshot


def collect_explicit_cli_fields(
    argv: Sequence[str] | None = None,
) -> frozenset[str]:
    """Return argparse destination names explicitly present in ``argv``.

    Only long public UAAF options exist, so scanning option tokens is sufficient
    and avoids altering the historical argparse defaults visible to callers.
    """
    tokens = list(sys.argv[1:] if argv is None else argv)
    explicit: set[str] = set()
    for token in tokens:
        if not isinstance(token, str):
            continue
        option = token.split("=", 1)[0]
        field_name = _CLI_OPTION_TO_FIELD.get(option)
        if field_name is not None:
            explicit.add(field_name)
    return frozenset(explicit)


def load_config_file(
    path: str | Path | None,
    *,
    cwd: str | Path | None = None,
) -> LoadedConfig:
    """Load one JSON, TOML, or deterministic-subset YAML configuration file."""
    if path is None:
        return LoadedConfig(path=None, data=MappingProxyType({}))

    base = _absolute_base(cwd)
    config_path = _resolve_path(path, base_dir=base, field_name="config")
    if not config_path.exists():
        raise ConfigFileError(f"Configuration file does not exist: {config_path}.")
    if not config_path.is_file():
        raise ConfigFileError(
            f"Configuration path is not a regular file: {config_path}."
        )

    suffix = config_path.suffix.casefold()
    if suffix not in SUPPORTED_CONFIG_SUFFIXES:
        expected = ", ".join(sorted(SUPPORTED_CONFIG_SUFFIXES))
        raise ConfigFileError(
            f"Unsupported configuration format {suffix!r} for {config_path}; "
            f"expected one of: {expected}."
        )

    try:
        text = config_path.read_text(encoding="utf-8")
    except UnicodeError as error:
        raise ConfigFileError(
            f"Configuration file is not valid UTF-8: {config_path}."
        ) from error
    except OSError as error:
        raise ConfigFileError(
            f"Unable to read configuration file: {config_path}."
        ) from error

    try:
        if suffix == ".json":
            data = {} if not text.strip() else json.loads(text)
        elif suffix == ".toml":
            data = {} if not text.strip() else tomllib.loads(text)
        else:
            data = _parse_simple_yaml(text)
    except (json.JSONDecodeError, tomllib.TOMLDecodeError) as error:
        format_name = "JSON" if suffix == ".json" else "TOML"
        raise ConfigFileError(
            f"Invalid {format_name} configuration syntax: {config_path}."
        ) from error
    except ConfigValidationError:
        raise
    except ValueError as error:
        raise ConfigFileError(
            f"Invalid YAML configuration syntax: {config_path}. {error}"
        ) from error

    if data is None:
        data = {}
    if not isinstance(data, Mapping):
        raise ConfigValidationError(
            f"UAAF configuration root must be a mapping in {config_path}."
        )

    selected = _select_uaaf_root(data, config_path=config_path)
    return LoadedConfig(
        path=config_path,
        data=_freeze_mapping(selected),
    )


def load_config(
    path: str | Path | None,
    *,
    cwd: str | Path | None = None,
) -> dict[str, Any]:
    """Compatibility wrapper returning a mutable defensive mapping."""
    return _thaw(load_config_file(path, cwd=cwd).data)


def resolve_global_config(
    *,
    cli_values: Mapping[str, Any] | None = None,
    explicit_cli_fields: Collection[str] = (),
    config_path: str | Path | None = None,
    cwd: str | Path | None = None,
    framework_root_default: str | Path | None = None,
    validate_directories: bool = True,
) -> ResolvedConfig:
    """Resolve defaults, file values, and explicit CLI values.

    Precedence is exact and field-based::

        framework defaults < configuration file < explicit CLI arguments
    """
    working_directory = _absolute_base(cwd)
    inferred_root = Path(__file__).resolve().parents[2]
    default_root = _resolve_path(
        framework_root_default if framework_root_default is not None else inferred_root,
        base_dir=working_directory,
        field_name="framework_root",
    )

    loaded = load_config_file(config_path, cwd=working_directory)
    file_base = loaded.path.parent if loaded.path is not None else working_directory
    file_overrides = overrides_from_mapping(loaded.data, base_dir=file_base)
    cli_overrides = overrides_from_cli(
        cli_values or {},
        explicit_fields=explicit_cli_fields,
        base_dir=working_directory,
    )

    project_path = _first_supplied(
        cli_overrides.project_path,
        file_overrides.project_path,
        working_directory,
    )
    auditors = _first_supplied(
        cli_overrides.auditors,
        file_overrides.auditors,
        DEFAULT_AUDITORS,
    )
    output_formats = _first_supplied(
        cli_overrides.output_formats,
        file_overrides.output_formats,
        DEFAULT_OUTPUT_FORMATS,
    )
    fail_on = _first_supplied(
        cli_overrides.fail_on,
        file_overrides.fail_on,
        DEFAULT_FAIL_ON,
    )
    framework_root = _first_supplied(
        cli_overrides.framework_root,
        file_overrides.framework_root,
        default_root,
    )
    plugins_dir = _first_supplied(
        cli_overrides.plugins_dir,
        file_overrides.plugins_dir,
        Path(framework_root) / "plugins",
    )
    output_dir = _first_supplied(
        cli_overrides.output_dir,
        file_overrides.output_dir,
        Path(framework_root) / "07_OUTPUTS",
    )

    file_exclusions = (
        () if file_overrides.exclude is UNSET else file_overrides.exclude
    )
    cli_exclusions = (
        () if cli_overrides.exclude is UNSET else cli_overrides.exclude
    )
    exclusions = tuple(merge_exclusions(file_exclusions, cli_exclusions))

    plugin_defaults = _first_supplied(
        cli_overrides.plugin_defaults,
        file_overrides.plugin_defaults,
        {},
    )
    plugin_configs = _first_supplied(
        cli_overrides.plugin_configs,
        file_overrides.plugin_configs,
        {},
    )

    resolved = ResolvedConfig(
        project_path=Path(project_path),
        auditors=tuple(auditors),
        output_formats=tuple(output_formats),
        config_path=loaded.path,
        fail_on=tuple(fail_on),
        exclude=exclusions,
        output_dir=Path(output_dir),
        plugins_dir=Path(plugins_dir),
        framework_root=Path(framework_root),
        plugin_defaults=plugin_defaults,
        plugin_configs=plugin_configs,
    )
    if validate_directories:
        validate_resolved_paths(resolved)
    return resolved


def overrides_from_cli(
    values: Mapping[str, Any],
    *,
    explicit_fields: Collection[str],
    base_dir: Path,
) -> ConfigOverrides:
    """Build typed overrides using only options explicitly present in CLI."""
    explicit = frozenset(explicit_fields)
    unknown = sorted(explicit - frozenset(_CLI_OPTION_TO_FIELD.values()))
    if unknown:
        raise ConfigValidationError(
            f"Unknown explicit CLI field(s): {unknown}."
        )

    kwargs: dict[str, Any] = {}
    if "project_path" in explicit:
        kwargs["project_path"] = _resolve_path(
            values.get("project_path"),
            base_dir=base_dir,
            field_name="project_path",
        )
    if "auditors" in explicit:
        kwargs["auditors"] = normalize_auditors(values.get("auditors"))
    if "output_formats" in explicit:
        kwargs["output_formats"] = normalize_output_formats(
            values.get("output_formats")
        )
    if "fail_on" in explicit:
        kwargs["fail_on"] = normalize_fail_on(values.get("fail_on"))
    if "exclude" in explicit:
        kwargs["exclude"] = tuple(merge_exclusions(values.get("exclude")))
    if "output_dir" in explicit:
        kwargs["output_dir"] = _resolve_path(
            values.get("output_dir"),
            base_dir=base_dir,
            field_name="output_dir",
        )
    if "plugins_dir" in explicit:
        kwargs["plugins_dir"] = _resolve_path(
            values.get("plugins_dir"),
            base_dir=base_dir,
            field_name="plugins_dir",
        )
    if "framework_root" in explicit:
        kwargs["framework_root"] = _resolve_path(
            values.get("framework_root"),
            base_dir=base_dir,
            field_name="framework_root",
        )
    return ConfigOverrides(**kwargs)


def overrides_from_mapping(
    mapping: Mapping[str, Any],
    *,
    base_dir: Path,
) -> ConfigOverrides:
    """Validate and normalize a partial mapping loaded from a file."""
    unknown = sorted(str(key) for key in mapping if key not in _GLOBAL_KEYS)
    if unknown:
        raise ConfigValidationError(
            f"Unknown global configuration field(s): {unknown}."
        )

    kwargs: dict[str, Any] = {}
    if "project_path" in mapping:
        kwargs["project_path"] = _resolve_path(
            mapping["project_path"],
            base_dir=base_dir,
            field_name="project_path",
        )

    plugin_alias_from_auditors: Mapping[str, Any] | None = None
    if "auditors" in mapping:
        auditors_value = mapping["auditors"]
        if isinstance(auditors_value, Mapping):
            plugin_alias_from_auditors = auditors_value
        else:
            kwargs["auditors"] = normalize_auditors(auditors_value)

    if "output_formats" in mapping:
        kwargs["output_formats"] = normalize_output_formats(
            mapping["output_formats"]
        )
    if "fail_on" in mapping:
        kwargs["fail_on"] = normalize_fail_on(mapping["fail_on"])

    exclusions: list[Any] = []
    if "exclude" in mapping:
        exclusions.append(mapping["exclude"])
    if "ignored_directories" in mapping:
        exclusions.append(mapping["ignored_directories"])
    if exclusions:
        kwargs["exclude"] = tuple(merge_exclusions(*exclusions))

    for field_name in ("output_dir", "plugins_dir", "framework_root"):
        if field_name in mapping:
            kwargs[field_name] = _resolve_path(
                mapping[field_name],
                base_dir=base_dir,
                field_name=field_name,
            )

    defaults = _resolve_mapping_alias(
        mapping,
        canonical="defaults",
        alias="global",
    )
    if defaults is not UNSET:
        kwargs["plugin_defaults"] = _validated_mapping(
            defaults,
            field_name="defaults",
        )

    plugins = mapping.get("plugins", UNSET)
    if plugins is not UNSET and plugin_alias_from_auditors is not None:
        if _plain_equal(plugins, plugin_alias_from_auditors):
            plugins = plugin_alias_from_auditors
        else:
            raise ConfigConflictError(
                "Configuration fields 'plugins' and mapping-valued 'auditors' "
                "provide conflicting plugin sections."
            )
    elif plugins is UNSET and plugin_alias_from_auditors is not None:
        plugins = plugin_alias_from_auditors

    if plugins is not UNSET:
        kwargs["plugin_configs"] = _validated_plugin_configs(plugins)
    return ConfigOverrides(**kwargs)


def validate_resolved_paths(config: ResolvedConfig) -> None:
    """Validate path kinds without creating output directories."""
    _require_existing_directory(config.project_path, "project_path")
    _require_existing_directory(config.framework_root, "framework_root")
    _require_existing_directory(config.plugins_dir, "plugins_dir")
    if config.output_dir.exists() and not config.output_dir.is_dir():
        raise ConfigValidationError(
            f"output_dir is not a directory: {config.output_dir}."
        )


def normalize_auditors(value: Any) -> tuple[str, ...]:
    """Normalize requested auditor selectors without resolving Registry aliases."""
    selectors = _split_csv(value, preserve_case=False, field_name="auditors")
    selectors = _deduplicate(selectors)
    if not selectors:
        raise ConfigValidationError("At least one auditor selector is required.")
    if "all" in selectors and selectors != ["all"]:
        raise ConfigValidationError(
            "'all' cannot be combined with explicit auditor selectors."
        )
    return tuple(selectors)


def normalize_output_formats(value: Any) -> tuple[str, ...]:
    """Normalize and validate requested report formats."""
    formats = _split_csv(
        value,
        preserve_case=False,
        field_name="output_formats",
    )
    normalized = ["markdown" if item == "md" else item for item in formats]
    normalized = _deduplicate(normalized)
    if not normalized:
        raise ConfigValidationError("At least one output format is required.")
    unknown = sorted(set(normalized) - VALID_OUTPUT_FORMATS)
    if unknown:
        raise ConfigValidationError(
            f"Unsupported output format(s): {unknown}. "
            "Use markdown, json, and/or sarif."
        )
    return tuple(normalized)


def normalize_fail_on(value: Any) -> tuple[str, ...]:
    """Normalize and validate finding severities used for exit status."""
    severities = _deduplicate(
        _split_csv(value, preserve_case=False, field_name="fail_on")
    )
    unknown = sorted(set(severities) - VALID_SEVERITIES)
    if unknown:
        raise ConfigValidationError(
            f"Unsupported severity value(s): {unknown}. "
            f"Expected {sorted(VALID_SEVERITIES)}."
        )
    return tuple(severities)


def merge_exclusions(*values: Any) -> list[str]:
    """Merge directory names in stable first-seen order, preserving case."""
    merged: list[str] = []
    seen: set[str] = set()
    for value in values:
        for item in _split_csv(
            value,
            preserve_case=True,
            field_name="exclude",
            allow_empty=True,
        ):
            name = item.strip()
            if not name:
                continue
            if (
                Path(name).name != name
                or "/" in name
                or "\\" in name
                or name in {".", ".."}
            ):
                raise ConfigValidationError(
                    "Excluded directory must be a directory name, not a path: "
                    f"{name!r}."
                )
            if name not in seen:
                seen.add(name)
                merged.append(name)
    return merged


def _select_uaaf_root(
    data: Mapping[str, Any],
    *,
    config_path: Path,
) -> Mapping[str, Any]:
    """Select direct UAAF data or ``[tool.uaaf]`` from a TOML document."""
    tool = data.get("tool")
    if not isinstance(tool, Mapping) or "uaaf" not in tool:
        return data

    uaaf = tool["uaaf"]
    if not isinstance(uaaf, Mapping):
        raise ConfigValidationError(
            f"Configuration section 'tool.uaaf' must be a mapping in {config_path}."
        )
    direct_keys = sorted(key for key in data if key in _GLOBAL_KEYS)
    if direct_keys:
        raise ConfigConflictError(
            "Configuration cannot combine direct UAAF fields with "
            f"'tool.uaaf': {direct_keys}."
        )
    return uaaf


def _resolve_mapping_alias(
    mapping: Mapping[str, Any],
    *,
    canonical: str,
    alias: str,
) -> Any:
    canonical_value = mapping.get(canonical, UNSET)
    alias_value = mapping.get(alias, UNSET)
    if canonical_value is UNSET:
        return alias_value
    if alias_value is UNSET:
        return canonical_value
    if not _plain_equal(canonical_value, alias_value):
        raise ConfigConflictError(
            f"Configuration fields {canonical!r} and {alias!r} conflict."
        )
    return canonical_value


def _validated_mapping(value: Any, *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigValidationError(
            f"Configuration field {field_name!r} must be a mapping."
        )
    result: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ConfigValidationError(
                f"Configuration field {field_name!r} must use non-empty string keys."
            )
        result[key] = _copy_plain(item)
    return result


def _validated_plugin_configs(value: Any) -> dict[str, dict[str, Any]]:
    sections = _validated_mapping(value, field_name="plugins")
    result: dict[str, dict[str, Any]] = {}
    for selector, section in sections.items():
        if not isinstance(section, Mapping):
            raise ConfigValidationError(
                f"Configuration for plugin {selector!r} must be a mapping."
            )
        result[selector] = _validated_mapping(
            section,
            field_name=f"plugins.{selector}",
        )
    return result


def _resolve_path(value: Any, *, base_dir: Path, field_name: str) -> Path:
    if isinstance(value, Path):
        candidate = value
    elif isinstance(value, str):
        if not value.strip():
            raise ConfigValidationError(
                f"Configuration path {field_name!r} cannot be empty."
            )
        candidate = Path(value)
    else:
        raise ConfigValidationError(
            f"Configuration path {field_name!r} must be a string or Path."
        )
    candidate = candidate.expanduser()
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


def _absolute_base(value: str | Path | None) -> Path:
    base = Path.cwd() if value is None else Path(value)
    return base.expanduser().resolve()


def _require_existing_directory(path: Path, field_name: str) -> None:
    if not path.exists():
        raise ConfigValidationError(f"{field_name} does not exist: {path}.")
    if not path.is_dir():
        raise ConfigValidationError(f"{field_name} is not a directory: {path}.")


def _first_supplied(*values: Any) -> Any:
    for value in values:
        if value is not UNSET:
            return value
    raise AssertionError("At least one configuration value must be supplied.")


def _split_csv(
    value: Any,
    *,
    preserve_case: bool,
    field_name: str,
    allow_empty: bool = False,
) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items: Sequence[Any] = (value,)
    elif isinstance(value, Sequence) and not isinstance(
        value,
        (bytes, bytearray),
    ):
        raw_items = value
    else:
        raise ConfigValidationError(
            f"Configuration field {field_name!r} must be a string or sequence of strings."
        )

    result: list[str] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, str):
            raise ConfigValidationError(
                f"Configuration field {field_name!r} must contain only strings."
            )
        parts = raw_item.split(",")
        for part in parts:
            stripped = part.strip()
            if not stripped:
                if allow_empty:
                    continue
                continue
            result.append(stripped if preserve_case else stripped.casefold())
    return result


def _deduplicate(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    frozen = {
        str(key): _freeze(item)
        for key, item in value.items()
    }
    return MappingProxyType(frozen)


def _freeze_plugin_configs(
    value: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Mapping[str, Any]]:
    frozen: dict[str, Mapping[str, Any]] = {}
    for key, section in value.items():
        frozen[str(key)] = _freeze_mapping(section)
    return MappingProxyType(frozen)


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return sorted(_thaw(item) for item in value)
    return value


def _copy_plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _copy_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_copy_plain(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_copy_plain(item) for item in value)
    if isinstance(value, set):
        return set(_copy_plain(item) for item in value)
    return value


def _ordered_plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _ordered_plain(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, tuple):
        return [_ordered_plain(item) for item in value]
    if isinstance(value, list):
        return [_ordered_plain(item) for item in value]
    if isinstance(value, frozenset | set):
        return sorted(_ordered_plain(item) for item in value)
    if isinstance(value, Path):
        return str(value)
    return value


def _redact(value: Any, *, key_name: str = "") -> Any:
    normalized_key = key_name.casefold().replace("-", "_")
    if any(part in normalized_key for part in _SENSITIVE_KEY_PARTS):
        return "<redacted>"
    if isinstance(value, Mapping):
        return {
            key: _redact(item, key_name=str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _plain_equal(first: Any, second: Any) -> bool:
    return _ordered_plain(first) == _ordered_plain(second)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the documented deterministic YAML subset used by UAAF.

    Supported constructs are indentation-based mappings, scalar lists, quoted
    and unquoted scalars, JSON-style inline lists/mappings, booleans, nulls,
    integers, and floats. Anchors, tags, multiline scalars, and list-of-mapping
    syntax are intentionally outside this dependency-free subset.
    """
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    lines = text.splitlines()
    for index, raw_line in enumerate(lines):
        line_number = index + 1
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indentation = raw_line[: len(raw_line) - len(raw_line.lstrip())]
        if "\t" in indentation:
            raise ValueError("YAML indentation must use spaces, not tabs.")
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        content = _strip_yaml_comment(raw_line.strip())
        if not content:
            continue
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ValueError(f"Invalid YAML indentation at line {line_number}.")
        parent = stack[-1][1]

        if content.startswith("- ") or content == "-":
            if not isinstance(parent, list):
                raise ValueError(
                    f"Unexpected YAML list item at line {line_number}."
                )
            item_text = content[1:].strip()
            if not item_text or ":" in item_text:
                raise ValueError(
                    "Nested or mapping YAML list items are not supported "
                    f"at line {line_number}."
                )
            parent.append(_parse_yaml_scalar(item_text))
            continue

        if ":" not in content:
            raise ValueError(
                f"Invalid YAML mapping entry at line {line_number}."
            )
        key, raw_value = content.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Empty YAML key at line {line_number}.")
        if not isinstance(parent, dict):
            raise ValueError(
                f"YAML mapping is not allowed at line {line_number}."
            )
        if key in parent:
            raise ValueError(
                f"Duplicate YAML key {key!r} at line {line_number}."
            )

        value_text = raw_value.strip()
        if value_text:
            parent[key] = _parse_yaml_scalar(value_text)
            continue

        next_content, next_indent = _next_yaml_content(lines, index + 1)
        if next_content is None or next_indent <= indent:
            parent[key] = {}
            continue
        child: Any = [] if next_content.startswith("-") else {}
        parent[key] = child
        stack.append((indent, child))
    return root


def _next_yaml_content(
    lines: Sequence[str],
    start: int,
) -> tuple[str | None, int]:
    for raw_line in lines[start:]:
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        return _strip_yaml_comment(raw_line.strip()), indent
    return None, -1


def _strip_yaml_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    output: list[str] = []
    for char in value:
        if escaped:
            output.append(char)
            escaped = False
            continue
        if char == "\\" and quote == '"':
            output.append(char)
            escaped = True
            continue
        if char in {"'", '"'}:
            quote = None if quote == char else char if quote is None else quote
            output.append(char)
            continue
        if char == "#" and quote is None:
            break
        output.append(char)
    if quote is not None:
        raise ValueError("Unterminated quoted YAML scalar.")
    return "".join(output).rstrip()


def _parse_yaml_scalar(value: str) -> Any:
    lowered = value.casefold()
    if lowered in {"null", "~"}:
        return None
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if value.startswith("[") and value.endswith("]"):
        try:
            return json.loads(value.replace("'", '"'))
        except json.JSONDecodeError:
            inner = value[1:-1].strip()
            if not inner:
                return []
            return [
                _parse_yaml_scalar(item.strip())
                for item in inner.split(",")
                if item.strip()
            ]
    if value.startswith("{"):
        try:
            return json.loads(value.replace("'", '"'))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid inline YAML value: {value!r}.") from error
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)", value):
        return float(value)
    if value.startswith(("|", ">", "&", "*", "!")):
        raise ValueError(f"Unsupported YAML scalar syntax: {value!r}.")
    return value


__all__ = [
    "ConfigConflictError",
    "ConfigFileError",
    "ConfigOverrides",
    "ConfigValidationError",
    "DEFAULT_AUDITORS",
    "DEFAULT_EXCLUSIONS",
    "DEFAULT_FAIL_ON",
    "DEFAULT_OUTPUT_FORMATS",
    "GlobalConfigError",
    "LoadedConfig",
    "ResolvedConfig",
    "SUPPORTED_CONFIG_SUFFIXES",
    "UNSET",
    "VALID_OUTPUT_FORMATS",
    "VALID_SEVERITIES",
    "collect_explicit_cli_fields",
    "load_config",
    "load_config_file",
    "merge_exclusions",
    "normalize_auditors",
    "normalize_fail_on",
    "normalize_output_formats",
    "overrides_from_cli",
    "overrides_from_mapping",
    "resolve_global_config",
    "validate_resolved_paths",
]
