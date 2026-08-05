"""Unified plugin discovery, execution, aggregation, and reporting for UAAF."""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Collection, Mapping, Sequence

from uaaf_core.audit.audit_result import (
    AuditExecution,
    AuditFinding,
    AuditResult,
    AuditStatus,
    FindingSeverity,
    validate_audit_result,
)
from uaaf_core.config import (
    DEFAULT_OUTPUT_FORMATS,
    VALID_OUTPUT_FORMATS,
    VALID_SEVERITIES,
    ConfigValidationError,
    ResolvedConfig,
    load_config,
    merge_exclusions,
    normalize_fail_on,
    normalize_output_formats,
    resolve_global_config,
)
from uaaf_core.contracts.processor import ProcessorContract
from uaaf_core.kernel import UAAFKernel
from uaaf_core.models.profile import AuditProfile
from uaaf_core.registry import (
    PluginDescriptor,
    PluginDiscoveryError,
    UAAFRegistry,
)
from uaaf_core.reporting.report_engine import ReportEngine
from uaaf_core.runtime.runtime_context import RuntimeContext

ORCHESTRATOR_ID = "uaaf-orchestrator"
ORCHESTRATOR_VERSION = "1.0.0"
PROFILE_ID = "uaaf-unified-cli"
RESULT_OUTPUT_KEY = "audit_result"
PLUGIN_CONTEXTS_KEY = "uaaf.plugin_contexts"


class OrchestratorError(RuntimeError):
    """Base exception for unified orchestration failures."""


@dataclass(slots=True)
class OrchestrationResult:
    """Complete output of one unified UAAF execution."""

    audit_results: list[dict[str, Any]]
    consolidated_result: dict[str, Any]
    report_paths: list[Path]
    runtime_context: RuntimeContext
    exit_code: int


class UnifiedOrchestrator:
    """Discover, execute, aggregate, and report UAAF auditor plugins."""

    def __init__(
        self,
        *,
        framework_root: str | Path | None = None,
        plugins_dir: str | Path | None = None,
        report_engine: ReportEngine | None = None,
        registry: UAAFRegistry | None = None,
    ) -> None:
        inferred_root = Path(__file__).resolve().parents[2]
        registry_root = getattr(registry, "framework_root", inferred_root)
        self.framework_root = Path(
            framework_root or registry_root
        ).expanduser().resolve()
        registry_plugins = getattr(
            registry,
            "plugins_dir",
            self.framework_root / "plugins",
        )
        self.plugins_dir = Path(
            plugins_dir or registry_plugins
        ).expanduser().resolve()
        self._registry_injected = registry is not None
        self.registry = (
            registry
            if registry is not None
            else UAAFRegistry(
                framework_root=self.framework_root,
                plugins_dir=self.plugins_dir,
            )
        )
        self.report_engine = report_engine or ReportEngine()

    def discover_plugins(self) -> list[PluginDescriptor]:
        """Delegate canonical plugin discovery to ``UAAFRegistry``."""
        return list(
            self.registry.discover_plugins(
                framework_root=self.framework_root,
                plugins_dir=self.plugins_dir,
            )
        )

    def run(
        self,
        *,
        project_path: str | Path,
        auditors: str | Sequence[str] = "all",
        output_formats: str | Sequence[str] = DEFAULT_OUTPUT_FORMATS,
        config_path: str | Path | None = None,
        fail_on: str | Sequence[str] = (),
        exclude: str | Sequence[str] = (),
        output_dir: str | Path | None = None,
        _explicit_fields: Collection[str] | None = None,
    ) -> OrchestrationResult:
        """Compatibility adapter that resolves legacy arguments canonically.

        Direct callers predating global configuration can continue using the
        historical keyword arguments.  Exact absence-versus-explicit semantics
        are available through ``_explicit_fields`` and are used by tests and
        adapters; the public CLI calls :meth:`run_resolved` directly.
        """
        cli_values = {
            "project_path": project_path,
            "auditors": auditors,
            "output_formats": output_formats,
            "fail_on": fail_on,
            "exclude": exclude,
            "output_dir": output_dir,
        }
        explicit_fields = (
            frozenset(_explicit_fields)
            if _explicit_fields is not None
            else _infer_legacy_explicit_fields(
                auditors=auditors,
                output_formats=output_formats,
                fail_on=fail_on,
                exclude=exclude,
                output_dir=output_dir,
            )
        )
        explicit_fields = frozenset({"project_path", *explicit_fields})
        resolved = resolve_global_config(
            cli_values=cli_values,
            explicit_cli_fields=explicit_fields,
            config_path=config_path,
            framework_root_default=self.framework_root,
            validate_directories=False,
        )
        return self.run_resolved(resolved)

    def run_resolved(self, config: ResolvedConfig) -> OrchestrationResult:
        """Execute one fully resolved and immutable global configuration."""
        if not isinstance(config, ResolvedConfig):
            raise TypeError(
                "UnifiedOrchestrator.run_resolved() requires ResolvedConfig."
            )

        self._configure_execution_paths(config)
        target_path = _require_directory(config.project_path, "project_path")
        destination = config.output_dir.expanduser().resolve()
        if destination.exists() and not destination.is_dir():
            raise NotADirectoryError(
                f"output_dir is not a directory: {destination}."
            )
        destination.mkdir(parents=True, exist_ok=True)

        self.discover_plugins()
        selected = list(self.registry.select_plugins(config.auditors))
        plugin_sources = _validated_plugin_sources(
            registry=self.registry,
            selected_plugins=selected,
            config=config,
        )
        plugin_contexts = {
            plugin.plugin_id: build_plugin_context(
                plugin=plugin,
                project_path=target_path,
                config=plugin_sources[plugin.plugin_id],
                exclusions=config.exclude,
                strict=True,
            )
            for plugin in selected
        }

        started_at = _utc_now_iso()
        with tempfile.TemporaryDirectory(prefix="uaaf_runtime_") as workspace:
            runtime = _build_runtime(
                project_path=target_path,
                output_dir=destination,
                workspace_dir=Path(workspace),
                selected_plugins=selected,
                plugin_contexts=plugin_contexts,
                registry=(
                    self.registry
                    if isinstance(self.registry, UAAFRegistry)
                    else None
                ),
                resolved_config=config,
            )
            runtime.run()
            audit_results = _extract_ordered_audit_results(
                runtime_context=runtime.context,
                selected_plugins=selected,
            )

        completed_at = _utc_now_iso()
        consolidated = build_consolidated_result(
            project_path=target_path,
            audit_results=audit_results,
            started_at=started_at,
            completed_at=completed_at,
        )
        report_paths = [
            self.report_engine.write_report(
                consolidated,
                format=output_format,
                output_dir=destination,
            )
            for output_format in config.output_formats
        ]
        exit_code = determine_exit_code(
            audit_results=audit_results,
            fail_on=config.fail_on,
        )
        return OrchestrationResult(
            audit_results=audit_results,
            consolidated_result=consolidated,
            report_paths=report_paths,
            runtime_context=runtime.context,
            exit_code=exit_code,
        )

    def _configure_execution_paths(self, config: ResolvedConfig) -> None:
        """Align Orchestrator and Registry paths with resolved configuration."""
        new_root = config.framework_root.expanduser().resolve()
        new_plugins = config.plugins_dir.expanduser().resolve()
        paths_changed = (
            new_root != self.framework_root
            or new_plugins != self.plugins_dir
        )
        self.framework_root = new_root
        self.plugins_dir = new_plugins
        if not paths_changed or self._registry_injected:
            return
        self.registry = UAAFRegistry(
            framework_root=self.framework_root,
            plugins_dir=self.plugins_dir,
        )


def discover_plugins(
    *,
    framework_root: str | Path,
    plugins_dir: str | Path,
) -> list[PluginDescriptor]:
    """Compatibility wrapper around canonical Registry discovery."""
    registry = UAAFRegistry(
        framework_root=framework_root,
        plugins_dir=plugins_dir,
    )
    return list(registry.discover_plugins())


def select_plugins(
    discovered: Sequence[PluginDescriptor],
    auditors: str | Sequence[str],
) -> list[PluginDescriptor]:
    """Compatibility wrapper around canonical Registry selection.

    The wrapper retains the pre-3.2 duplicate-selector rejection expected by
    existing direct callers. The Registry method itself follows the new
    contract and deduplicates selectors while preserving deterministic plugin
    order.
    """
    registry = UAAFRegistry()
    for plugin in discovered:
        registry.register_plugin(plugin)
    return list(
        registry.select_plugins(
            auditors,
            reject_duplicate_selectors=True,
        )
    )


def build_plugin_context(
    *,
    plugin: PluginDescriptor,
    project_path: Path,
    config: Mapping[str, Any],
    exclusions: Sequence[str],
    strict: bool = False,
) -> dict[str, Any]:
    """Build one isolated plugin context.

    ``strict=False`` preserves the historical compatibility wrapper that
    filters unsupported keys.  Canonical resolved execution uses
    ``strict=True`` after Registry-aware validation.
    """
    context: dict[str, Any] = {
        "project_path": str(project_path.resolve()),
        "audit_type": plugin.audit_type,
    }
    defaults = config.get("defaults", config.get("global", {}))
    if defaults is not None:
        if not isinstance(defaults, Mapping):
            raise TypeError("Configuration 'defaults' must be a mapping.")
        context.update(defaults)

    plugin_sections = config.get("plugins", config.get("auditors", {}))
    if plugin_sections is not None:
        if not isinstance(plugin_sections, Mapping):
            raise TypeError("Configuration 'plugins' must be a mapping.")
        for key in (plugin.name, plugin.audit_type, plugin.plugin_id):
            section = plugin_sections.get(key)
            if section is None:
                continue
            if not isinstance(section, Mapping):
                raise TypeError(
                    f"Configuration for auditor {key!r} must be a mapping."
                )
            context.update(section)

    if exclusions and (
        not plugin.allowed_context_fields
        or "ignored_directories" in plugin.allowed_context_fields
    ):
        existing = context.get("ignored_directories", ())
        context["ignored_directories"] = merge_exclusions(
            existing,
            exclusions,
        )

    if plugin.allowed_context_fields:
        unknown = sorted(
            set(context)
            - plugin.allowed_context_fields
            - {"project_path", "audit_type"}
        )
        if strict and unknown:
            raise ConfigValidationError(
                f"Unsupported configuration field(s) for plugin "
                f"{plugin.plugin_id!r}: {unknown}."
            )
        for key in unknown:
            context.pop(key, None)

    context["project_path"] = str(project_path.resolve())
    if (
        not plugin.allowed_context_fields
        or "audit_type" in plugin.allowed_context_fields
    ):
        context["audit_type"] = plugin.audit_type
    return context


def _validated_plugin_sources(
    *,
    registry: Any,
    selected_plugins: Sequence[PluginDescriptor],
    config: ResolvedConfig,
) -> dict[str, dict[str, Any]]:
    """Resolve plugin aliases and validate all plugin-specific fields."""
    canonical_sections: dict[str, dict[str, Any]] = {}
    canonical_aliases: dict[str, str] = {}
    for selector, raw_section in config.plugin_configs.items():
        plugin = registry.resolve_plugin(selector)
        section = dict(raw_section)
        _reject_reserved_plugin_fields(section, selector=selector)
        _validate_plugin_fields(plugin, section, selector=selector)
        existing = canonical_sections.get(plugin.plugin_id)
        if existing is not None and existing != section:
            previous = canonical_aliases[plugin.plugin_id]
            raise ConfigValidationError(
                f"Plugin configuration aliases {previous!r} and {selector!r} "
                f"resolve to {plugin.plugin_id!r} with conflicting values."
            )
        canonical_sections[plugin.plugin_id] = section
        canonical_aliases[plugin.plugin_id] = selector

    selected = tuple(selected_plugins)
    defaults = dict(config.plugin_defaults)
    _reject_reserved_plugin_fields(defaults, selector="defaults")
    if defaults:
        known_plugins = (
            tuple(registry.list_plugins())
            if hasattr(registry, "list_plugins")
            else selected
        )
        declared_fields = set().union(
            *(
                set(plugin.allowed_context_fields)
                for plugin in known_plugins
                if plugin.allowed_context_fields
            )
        )
        if declared_fields:
            unknown_defaults = sorted(set(defaults) - declared_fields)
            if unknown_defaults:
                raise ConfigValidationError(
                    "Unsupported global plugin default field(s): "
                    f"{unknown_defaults}."
                )

    sources: dict[str, dict[str, Any]] = {}
    for plugin in selected:
        if plugin.allowed_context_fields:
            plugin_defaults = {
                key: value
                for key, value in defaults.items()
                if key in plugin.allowed_context_fields
            }
        else:
            plugin_defaults = dict(defaults)
        sources[plugin.plugin_id] = {
            "defaults": plugin_defaults,
            "plugins": {
                plugin.plugin_id: dict(
                    canonical_sections.get(plugin.plugin_id, {})
                )
            },
        }
    return sources


def _reject_reserved_plugin_fields(
    section: Mapping[str, Any],
    *,
    selector: str,
) -> None:
    reserved = sorted(set(section) & {"project_path", "audit_type"})
    if reserved:
        raise ConfigValidationError(
            f"Plugin configuration {selector!r} cannot override reserved "
            f"field(s): {reserved}."
        )


def _validate_plugin_fields(
    plugin: PluginDescriptor,
    section: Mapping[str, Any],
    *,
    selector: str,
) -> None:
    if not plugin.allowed_context_fields:
        return
    unknown = sorted(set(section) - plugin.allowed_context_fields)
    if unknown:
        raise ConfigValidationError(
            f"Unsupported configuration field(s) for plugin selector "
            f"{selector!r}: {unknown}."
        )


def _infer_legacy_explicit_fields(
    *,
    auditors: str | Sequence[str],
    output_formats: str | Sequence[str],
    fail_on: str | Sequence[str],
    exclude: str | Sequence[str],
    output_dir: str | Path | None,
) -> frozenset[str]:
    explicit: set[str] = set()
    if normalize_auditors_for_comparison(auditors) != ("all",):
        explicit.add("auditors")
    if normalize_output_formats(output_formats) != DEFAULT_OUTPUT_FORMATS:
        explicit.add("output_formats")
    if normalize_fail_on(fail_on):
        explicit.add("fail_on")
    if merge_exclusions(exclude):
        explicit.add("exclude")
    if output_dir is not None:
        explicit.add("output_dir")
    return frozenset(explicit)


def normalize_auditors_for_comparison(
    value: str | Sequence[str],
) -> tuple[str, ...]:
    if isinstance(value, str):
        raw_items: Sequence[str] = (value,)
    else:
        raw_items = value
    normalized: list[str] = []
    for item in raw_items:
        if not isinstance(item, str):
            raise TypeError("Auditor selectors must contain strings.")
        normalized.extend(
            part.strip().casefold()
            for part in item.split(",")
            if part.strip()
        )
    return tuple(dict.fromkeys(normalized))


def build_consolidated_result(
    *,
    project_path: Path,
    audit_results: Sequence[Mapping[str, Any]],
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    """Aggregate ordered plugin results into one canonical AuditResult."""
    normalized_results: list[dict[str, Any]] = []
    findings: list[AuditFinding] = []
    errors: list[str] = []
    severity_counts = {severity: 0 for severity in VALID_SEVERITIES}
    status_counts: dict[str, int] = {}
    total_duration_ms = 0

    for raw_result in audit_results:
        result = dict(raw_result)
        validate_audit_result(result)
        normalized_results.append(result)
        status = str(result["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
        execution = result.get("execution", {})
        duration = execution.get("duration_ms")
        if isinstance(duration, int) and not isinstance(duration, bool):
            total_duration_ms += duration
        for raw_finding in result["findings"]:
            severity = FindingSeverity(str(raw_finding["severity"]).lower())
            severity_counts[severity.value] += 1
            details = dict(raw_finding.get("details", {}))
            details.setdefault("source_plugin_id", result["plugin_id"])
            details.setdefault("source_audit_type", result["audit_type"])
            findings.append(
                AuditFinding(
                    code=str(raw_finding["code"]),
                    severity=severity,
                    path=str(raw_finding["path"]),
                    message=str(raw_finding["message"]),
                    details=details,
                )
            )
        for error in result["errors"]:
            errors.append(f"{result['plugin_id']}: {error}")

    if errors or status_counts.get(AuditStatus.FAILED.value, 0):
        status = AuditStatus.COMPLETED_WITH_ERRORS
    elif findings:
        status = AuditStatus.COMPLETED_WITH_FINDINGS
    else:
        status = AuditStatus.COMPLETED

    started = _parse_iso_datetime(started_at)
    completed = _parse_iso_datetime(completed_at)
    duration_ms = max(0, int((completed - started).total_seconds() * 1000))
    result = AuditResult(
        plugin_id=ORCHESTRATOR_ID,
        plugin_version=ORCHESTRATOR_VERSION,
        audit_type="consolidated",
        status=status,
        summary={
            "project_path": str(project_path.resolve()),
            "auditor_count": len(normalized_results),
            "auditors": [result["audit_type"] for result in normalized_results],
            "plugin_ids": [result["plugin_id"] for result in normalized_results],
            "audit_results": normalized_results,
            "status_counts": dict(sorted(status_counts.items())),
        },
        metrics={
            "auditor_count": len(normalized_results),
            "completed_auditor_count": status_counts.get(AuditStatus.COMPLETED.value, 0),
            "auditors_with_findings_count": status_counts.get(
                AuditStatus.COMPLETED_WITH_FINDINGS.value, 0
            ),
            "auditors_with_errors_count": status_counts.get(
                AuditStatus.COMPLETED_WITH_ERRORS.value, 0
            ),
            "failed_auditor_count": status_counts.get(AuditStatus.FAILED.value, 0),
            "findings_count": len(findings),
            "execution_error_count": len(errors),
            "critical_count": severity_counts[FindingSeverity.CRITICAL.value],
            "error_count": severity_counts[FindingSeverity.ERROR.value],
            "warning_count": severity_counts[FindingSeverity.WARNING.value],
            "info_count": severity_counts[FindingSeverity.INFO.value],
            "plugins_duration_ms": total_duration_ms,
        },
        findings=tuple(findings),
        errors=tuple(errors),
        execution=AuditExecution(
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        ),
    )
    return result.to_dict()


def determine_exit_code(
    *,
    audit_results: Sequence[Mapping[str, Any]],
    fail_on: Sequence[str],
) -> int:
    """Return 0, 1 for matching findings, or 2 for execution failures."""
    for result in audit_results:
        if result.get("errors") or result.get("status") in {
            AuditStatus.FAILED.value,
            AuditStatus.COMPLETED_WITH_ERRORS.value,
        }:
            return 2
    fail_set = set(normalize_fail_on(fail_on))
    if not fail_set:
        return 0
    for result in audit_results:
        for finding in result.get("findings", []):
            if str(finding.get("severity", "")).lower() in fail_set:
                return 1
    return 0


def _build_runtime(
    *,
    project_path: Path,
    output_dir: Path,
    workspace_dir: Path,
    selected_plugins: Sequence[PluginDescriptor],
    plugin_contexts: Mapping[str, dict[str, Any]],
    registry: UAAFRegistry | None = None,
    resolved_config: ResolvedConfig | None = None,
):
    runtime_registry = registry if registry is not None else UAAFRegistry()
    for plugin in selected_plugins:
        runtime_registry.register_processor(
            _processor_type_for(plugin),
            replace=True,
        )
    profile = AuditProfile(
        profile_id=PROFILE_ID,
        name="UAAF Unified CLI",
        version=ORCHESTRATOR_VERSION,
        description="Dynamically discovered unified auditor profile.",
        processor_ids=tuple(plugin.plugin_id for plugin in selected_plugins),
        plugin_ids=tuple(plugin.plugin_id for plugin in selected_plugins),
        configuration={"auditor_count": len(selected_plugins)},
    )
    runtime_registry.register_profile(profile, replace=True)
    kernel = UAAFKernel(registry=runtime_registry)
    return kernel.create_runtime(
        target_path=project_path,
        profile_id=PROFILE_ID,
        output_path=output_dir,
        workspace_path=workspace_dir,
        session_context={PLUGIN_CONTEXTS_KEY: dict(plugin_contexts)},
        runtime_metadata={
            "orchestrator_id": ORCHESTRATOR_ID,
            "orchestrator_version": ORCHESTRATOR_VERSION,
            "selected_plugin_ids": [plugin.plugin_id for plugin in selected_plugins],
            "resolved_config": (
                resolved_config.to_dict()
                if resolved_config is not None
                else None
            ),
        },
    )


def _processor_type_for(plugin: PluginDescriptor) -> type[ProcessorContract]:
    descriptor = plugin

    class DynamicAuditorProcessor(ProcessorContract):
        processor_id = descriptor.plugin_id
        processor_version = descriptor.plugin_version
        processor_description = f"Runtime adapter for {descriptor.name}."

        def validate(self, session: Any) -> None:
            contexts = session.get_context(PLUGIN_CONTEXTS_KEY, {})
            if not isinstance(contexts, Mapping):
                raise TypeError(f"{PLUGIN_CONTEXTS_KEY!r} must be a mapping.")
            context = contexts.get(self.processor_id)
            if not isinstance(context, dict):
                raise TypeError(
                    f"Plugin context for {self.processor_id!r} must be a dictionary."
                )

        def execute(self, session: Any) -> None:
            contexts = session.get_context(PLUGIN_CONTEXTS_KEY)
            plugin_context = dict(contexts[self.processor_id])
            try:
                audit_result = descriptor.runner(plugin_context)
                validate_audit_result(audit_result)
            except Exception as error:
                audit_result = _failed_plugin_result(
                    plugin=descriptor,
                    project_path=Path(plugin_context["project_path"]),
                    error=error,
                )
            session.set_context(f"uaaf.audit_result:{self.processor_id}", audit_result)
            self.add_output(RESULT_OUTPUT_KEY, audit_result)
            if audit_result["status"] != AuditStatus.COMPLETED.value:
                self.add_warning(
                    f"{self.processor_id} completed with status {audit_result['status']}."
                )

    DynamicAuditorProcessor.__name__ = (
        "Dynamic" + re.sub(r"[^A-Za-z0-9]", "", descriptor.name.title()) + "Processor"
    )
    DynamicAuditorProcessor.__qualname__ = DynamicAuditorProcessor.__name__
    return DynamicAuditorProcessor


def _failed_plugin_result(
    *,
    plugin: PluginDescriptor,
    project_path: Path,
    error: Exception,
) -> dict[str, Any]:
    timestamp = _utc_now_iso()
    message = str(error).strip()
    formatted = f"{type(error).__name__}: {message}" if message else type(error).__name__
    return AuditResult(
        plugin_id=plugin.plugin_id,
        plugin_version=plugin.plugin_version,
        audit_type=plugin.audit_type,
        status=AuditStatus.FAILED,
        summary={"project_path": str(project_path.resolve())},
        metrics={"findings_count": 0},
        findings=(),
        errors=(formatted,),
        execution=AuditExecution(
            started_at=timestamp,
            completed_at=timestamp,
            duration_ms=0,
        ),
    ).to_dict()


def _extract_ordered_audit_results(
    *,
    runtime_context: RuntimeContext,
    selected_plugins: Sequence[PluginDescriptor],
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for processor_result in runtime_context.list_processor_results():
        candidate = processor_result.outputs.get(RESULT_OUTPUT_KEY)
        if isinstance(candidate, Mapping):
            normalized = dict(candidate)
            validate_audit_result(normalized)
            by_id[processor_result.processor_id] = normalized
    missing = [plugin.plugin_id for plugin in selected_plugins if plugin.plugin_id not in by_id]
    if missing:
        raise OrchestratorError(f"Runtime did not return results for plugins: {missing}.")
    return [by_id[plugin.plugin_id] for plugin in selected_plugins]


def _require_directory(value: str | Path, field_name: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"{field_name} does not exist: {path}.")
    if not path.is_dir():
        raise NotADirectoryError(f"{field_name} is not a directory: {path}.")
    return path


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Execution timestamps must include timezone information.")
    return parsed.astimezone(UTC)


__all__ = [
    "DEFAULT_OUTPUT_FORMATS",
    "ORCHESTRATOR_ID",
    "ORCHESTRATOR_VERSION",
    "OrchestrationResult",
    "OrchestratorError",
    "PluginDescriptor",
    "PluginDiscoveryError",
    "UnifiedOrchestrator",
    "build_consolidated_result",
    "build_plugin_context",
    "determine_exit_code",
    "discover_plugins",
    "load_config",
    "merge_exclusions",
    "normalize_fail_on",
    "normalize_output_formats",
    "select_plugins",
]
