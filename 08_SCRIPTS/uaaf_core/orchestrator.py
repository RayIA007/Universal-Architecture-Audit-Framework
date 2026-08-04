"""Unified plugin discovery, execution, aggregation, and reporting for UAAF."""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from uaaf_core.audit.audit_result import (
    AuditExecution,
    AuditFinding,
    AuditResult,
    AuditStatus,
    FindingSeverity,
    validate_audit_result,
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
DEFAULT_OUTPUT_FORMATS = ("markdown", "json")
VALID_OUTPUT_FORMATS = frozenset(DEFAULT_OUTPUT_FORMATS)
VALID_SEVERITIES = frozenset(severity.value for severity in FindingSeverity)
_ORCHESTRATOR_CONFIG_KEYS = frozenset(
    {
        "auditors",
        "plugins",
        "defaults",
        "global",
        "exclude",
        "ignored_directories",
        "output_formats",
        "fail_on",
        "project_path",
        "output_dir",
    }
)


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
    ) -> OrchestrationResult:
        """Execute the selected auditors and generate consolidated reports."""
        target_path = _require_directory(project_path, "project_path")
        destination = Path(output_dir or self.framework_root / "07_OUTPUTS").expanduser().resolve()
        destination.mkdir(parents=True, exist_ok=True)

        config = load_config(config_path) if config_path else {}
        discovered = self.discover_plugins()
        selected = list(self.registry.select_plugins(auditors))
        formats = normalize_output_formats(
            output_formats if output_formats else config.get("output_formats", DEFAULT_OUTPUT_FORMATS)
        )
        fail_severities = normalize_fail_on(
            fail_on if fail_on else config.get("fail_on", ())
        )
        exclusions = merge_exclusions(
            config.get("exclude", config.get("ignored_directories", ())),
            exclude,
        )
        plugin_contexts = {
            plugin.plugin_id: build_plugin_context(
                plugin=plugin,
                project_path=target_path,
                config=config,
                exclusions=exclusions,
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
            for output_format in formats
        ]
        exit_code = determine_exit_code(
            audit_results=audit_results,
            fail_on=fail_severities,
        )
        return OrchestrationResult(
            audit_results=audit_results,
            consolidated_result=consolidated,
            report_paths=report_paths,
            runtime_context=runtime.context,
            exit_code=exit_code,
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
) -> dict[str, Any]:
    """Build a strict plugin context from global and plugin-specific config."""
    context: dict[str, Any] = {
        "project_path": str(project_path.resolve()),
        "audit_type": plugin.audit_type,
    }
    defaults = config.get("defaults", config.get("global", {}))
    if defaults is not None:
        if not isinstance(defaults, Mapping):
            raise TypeError("Configuration 'defaults' must be a mapping.")
        context.update(defaults)

    plugin_sections = config.get("auditors", config.get("plugins", {}))
    if plugin_sections is not None:
        if not isinstance(plugin_sections, Mapping):
            raise TypeError("Configuration 'auditors' must be a mapping.")
        for key in (plugin.name, plugin.audit_type, plugin.plugin_id):
            section = plugin_sections.get(key)
            if section is None:
                continue
            if not isinstance(section, Mapping):
                raise TypeError(f"Configuration for auditor {key!r} must be a mapping.")
            context.update(section)

    if exclusions:
        existing = context.get("ignored_directories", ())
        context["ignored_directories"] = merge_exclusions(existing, exclusions)

    if plugin.allowed_context_fields:
        unknown = set(context) - plugin.allowed_context_fields
        for key in unknown:
            context.pop(key, None)
    context["project_path"] = str(project_path.resolve())
    if not plugin.allowed_context_fields or "audit_type" in plugin.allowed_context_fields:
        context["audit_type"] = plugin.audit_type
    return context


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


def normalize_output_formats(value: str | Sequence[str]) -> tuple[str, ...]:
    """Normalize and validate requested report formats."""
    formats = _split_csv(value)
    if not formats:
        raise ValueError("At least one output format is required.")
    normalized = ["markdown" if item == "md" else item for item in formats]
    unknown = sorted(set(normalized) - VALID_OUTPUT_FORMATS)
    if unknown:
        raise ValueError(
            f"Unsupported output format(s): {unknown}. Use markdown and/or json."
        )
    return tuple(dict.fromkeys(normalized))


def normalize_fail_on(value: str | Sequence[str]) -> tuple[str, ...]:
    """Normalize and validate finding severities used for exit status."""
    severities = _split_csv(value)
    unknown = sorted(set(severities) - VALID_SEVERITIES)
    if unknown:
        raise ValueError(
            f"Unsupported severity value(s): {unknown}. Expected {sorted(VALID_SEVERITIES)}."
        )
    return tuple(dict.fromkeys(severities))


def merge_exclusions(*values: Any) -> list[str]:
    """Merge comma-separated or sequence exclusions in stable first-seen order."""
    merged: list[str] = []
    seen: set[str] = set()
    for value in values:
        for item in _split_csv_preserve_case(value):
            name = item.strip()
            if not name:
                continue
            if Path(name).name != name:
                raise ValueError(
                    f"Excluded directory must be a directory name, not a path: {name!r}."
                )
            if name not in seen:
                seen.add(name)
                merged.append(name)
    return merged


def load_config(path: str | Path | None) -> dict[str, Any]:
    """Load JSON, TOML, or YAML configuration; missing files are optional."""
    if path is None:
        return {}
    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        return {}
    if not config_path.is_file():
        raise ValueError(f"Configuration path is not a file: {config_path}.")
    text = config_path.read_text(encoding="utf-8")
    suffix = config_path.suffix.lower()
    if suffix == ".json":
        data = json.loads(text)
    elif suffix == ".toml":
        import tomllib

        data = tomllib.loads(text)
    elif suffix in {".yaml", ".yml"}:
        data = _load_yaml(text)
    else:
        raise ValueError(
            f"Unsupported configuration format {suffix!r}; use .json, .toml, .yaml, or .yml."
        )
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise TypeError("UAAF configuration root must be a mapping.")
    return dict(data)


def _load_yaml(text: str) -> Any:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return _parse_simple_yaml(text)
    return yaml.safe_load(text)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse a deterministic YAML subset used by ``uaaf.yaml``."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    lines = text.splitlines()
    for index, raw_line in enumerate(lines):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if "\t" in raw_line[: len(raw_line) - len(raw_line.lstrip())]:
            raise ValueError("YAML indentation must use spaces, not tabs.")
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        content = _strip_yaml_comment(raw_line.strip())
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ValueError(f"Invalid YAML indentation at line {index + 1}.")
        parent = stack[-1][1]
        if content.startswith("- ") or content == "-":
            if not isinstance(parent, list):
                raise ValueError(f"Unexpected YAML list item at line {index + 1}.")
            parent.append(_parse_yaml_scalar(content[1:].strip()))
            continue
        if ":" not in content:
            raise ValueError(f"Invalid YAML mapping entry at line {index + 1}.")
        key, raw_value = content.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Empty YAML key at line {index + 1}.")
        if not isinstance(parent, dict):
            raise ValueError(f"YAML mapping not allowed at line {index + 1}.")
        value_text = raw_value.strip()
        if value_text:
            parent[key] = _parse_yaml_scalar(value_text)
            continue
        next_content, next_indent = _next_yaml_content(lines, index + 1)
        child: Any = [] if next_content is not None and next_indent > indent and next_content.startswith("-") else {}
        parent[key] = child
        stack.append((indent, child))
    return root


def _next_yaml_content(lines: Sequence[str], start: int) -> tuple[str | None, int]:
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
    return "".join(output).rstrip()


def _parse_yaml_scalar(value: str) -> Any:
    lowered = value.casefold()
    if lowered in {"null", "~"}:
        return None
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if value.startswith("[") or value.startswith("{"):
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
    return value


def _build_runtime(
    *,
    project_path: Path,
    output_dir: Path,
    workspace_dir: Path,
    selected_plugins: Sequence[PluginDescriptor],
    plugin_contexts: Mapping[str, dict[str, Any]],
    registry: UAAFRegistry | None = None,
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


def _split_csv(value: Any) -> list[str]:
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


def _split_csv_preserve_case(value: Any) -> list[str]:
    if value is None:
        return []
    raw_items = [value] if isinstance(value, str) else list(value)
    items: list[str] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, str):
            raise TypeError("Comma-separated values must contain strings.")
        items.extend(
            part.strip()
            for part in raw_item.split(",")
            if part.strip()
        )
    return items


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