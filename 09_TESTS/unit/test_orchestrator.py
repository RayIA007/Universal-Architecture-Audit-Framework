"""Deterministic unit tests for the UAAF unified orchestrator."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "08_SCRIPTS"
for import_root in (PROJECT_ROOT, SCRIPTS_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from uaaf_core.audit.audit_result import (  # noqa: E402
    AuditExecution,
    AuditFinding,
    AuditResult,
    AuditStatus,
    FindingSeverity,
    validate_audit_result,
)
from uaaf_core.orchestrator import (  # noqa: E402
    ORCHESTRATOR_ID,
    OrchestratorError,
    PluginDescriptor,
    PluginDiscoveryError,
    UnifiedOrchestrator,
    build_consolidated_result,
    build_plugin_context,
    determine_exit_code,
    discover_plugins,
    load_config,
    merge_exclusions,
    normalize_fail_on,
    normalize_output_formats,
    select_plugins,
)
from uaaf_core.runtime.runtime_context import RuntimeContext  # noqa: E402

FIXED_STARTED = "2026-08-02T12:00:00+00:00"
FIXED_COMPLETED = "2026-08-02T12:00:00.010000+00:00"


def _module(name: str = "fixture") -> ModuleType:
    return ModuleType(name)


def _descriptor(
    name: str,
    *,
    plugin_id: str | None = None,
    audit_type: str | None = None,
    allowed: frozenset[str] | None = None,
) -> PluginDescriptor:
    module = _module(name)
    return PluginDescriptor(
        name=name,
        audit_type=audit_type or name,
        plugin_id=plugin_id or f"{name}-auditor",
        plugin_version="1.0.0",
        package_dir=Path("plugins") / name,
        module_path=Path("plugins") / name / f"{name}_auditor.py",
        runner=lambda _context: {},
        module=module,
        allowed_context_fields=allowed or frozenset(),
    )


def _result(
    *,
    plugin_id: str = "alpha-auditor",
    audit_type: str = "alpha",
    status: AuditStatus = AuditStatus.COMPLETED,
    findings: tuple[AuditFinding, ...] = (),
    errors: tuple[str, ...] = (),
) -> dict[str, Any]:
    return AuditResult(
        plugin_id=plugin_id,
        plugin_version="1.0.0",
        audit_type=audit_type,
        status=status,
        summary={"project_path": "."},
        metrics={"findings_count": len(findings)},
        findings=findings,
        errors=errors,
        execution=AuditExecution(
            started_at=FIXED_STARTED,
            completed_at=FIXED_COMPLETED,
            duration_ms=10,
        ),
    ).to_dict()


def _finding(severity: FindingSeverity) -> AuditFinding:
    return AuditFinding(
        code=f"TEST-{severity.value.upper()}-001",
        severity=severity,
        path="sample.py",
        message="Deterministic finding.",
        details={"rule": "fixture"},
    )


def _write_plugin(
    framework_root: Path,
    name: str,
    *,
    plugin_id: str | None = None,
    audit_type: str | None = None,
    severity: str | None = None,
    fail: bool = False,
    include_run: bool = True,
    include_init: bool = True,
) -> Path:
    package_dir = framework_root / "plugins" / name
    package_dir.mkdir(parents=True, exist_ok=True)
    if include_init:
        (package_dir / "__init__.py").write_text("", encoding="utf-8")
    finding_literal = "[]"
    status = "completed"
    if severity:
        finding_literal = repr(
            [
                {
                    "code": f"{name.upper()}-001",
                    "severity": severity,
                    "path": f"{name}.py",
                    "message": f"{name} finding",
                    "details": {"fixture": True},
                }
            ]
        )
        status = "completed_with_findings"
    run_source = ""
    if include_run:
        if fail:
            run_source = """
def run(context):
    global LAST_CONTEXT
    LAST_CONTEXT = dict(context)
    raise RuntimeError("deterministic plugin failure")
"""
        else:
            run_source = f"""
def run(context):
    global LAST_CONTEXT
    LAST_CONTEXT = dict(context)
    return {{
        "plugin_id": PLUGIN_ID,
        "plugin_version": PLUGIN_VERSION,
        "audit_type": AUDIT_TYPE,
        "status": {status!r},
        "summary": {{"project_path": context["project_path"]}},
        "metrics": {{"findings_count": len({finding_literal})}},
        "findings": {finding_literal},
        "errors": [],
        "execution": {{
            "started_at": {FIXED_STARTED!r},
            "completed_at": {FIXED_COMPLETED!r},
            "duration_ms": 10,
        }},
    }}
"""
    source = f'''PLUGIN_ID = {plugin_id or f"{name}-auditor"!r}
PLUGIN_VERSION = "1.0.0"
AUDIT_TYPE = {audit_type or name!r}
_ALLOWED_CONTEXT_FIELDS = {{
    "project_path",
    "audit_type",
    "ignored_directories",
    "threshold",
}}
LAST_CONTEXT = None
{run_source}
'''
    module_path = package_dir / f"{name}_auditor.py"
    module_path.write_text(source, encoding="utf-8")
    return package_dir


def _framework(tmp_path: Path) -> Path:
    root = tmp_path / "framework"
    (root / "plugins").mkdir(parents=True)
    return root


def test_discover_plugins_returns_sorted_descriptors(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "zeta")
    _write_plugin(root, "alpha")
    discovered = discover_plugins(framework_root=root, plugins_dir=root / "plugins")
    assert [plugin.name for plugin in discovered] == ["alpha", "zeta"]


def test_discover_plugins_skips_directory_without_init(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "valid")
    _write_plugin(root, "invalid", include_init=False)
    discovered = discover_plugins(framework_root=root, plugins_dir=root / "plugins")
    assert [plugin.name for plugin in discovered] == ["valid"]


def test_discover_plugins_skips_directory_without_auditor_file(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    package = root / "plugins" / "empty"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    _write_plugin(root, "valid")
    discovered = discover_plugins(framework_root=root, plugins_dir=root / "plugins")
    assert [plugin.name for plugin in discovered] == ["valid"]


def test_discover_plugins_requires_at_least_one_plugin(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    with pytest.raises(PluginDiscoveryError, match="No auditor plugins"):
        discover_plugins(framework_root=root, plugins_dir=root / "plugins")


def test_discover_plugins_requires_callable_run(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "broken", include_run=False)
    with pytest.raises(PluginDiscoveryError, match="callable run"):
        discover_plugins(framework_root=root, plugins_dir=root / "plugins")


def test_discover_plugins_rejects_duplicate_plugin_ids(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "alpha", plugin_id="same-auditor")
    _write_plugin(root, "beta", plugin_id="same-auditor")
    with pytest.raises(PluginDiscoveryError, match="Duplicate plugin identifiers"):
        discover_plugins(framework_root=root, plugins_dir=root / "plugins")


def test_discovered_descriptor_reads_module_metadata(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "alpha", plugin_id="custom-id", audit_type="custom-type")
    plugin = discover_plugins(framework_root=root, plugins_dir=root / "plugins")[0]
    assert plugin.plugin_id == "custom-id"
    assert plugin.audit_type == "custom-type"
    assert plugin.plugin_version == "1.0.0"


def test_select_plugins_all_returns_all() -> None:
    plugins = [_descriptor("alpha"), _descriptor("beta")]
    assert select_plugins(plugins, "all") == plugins


def test_select_plugins_empty_selector_means_all() -> None:
    plugins = [_descriptor("alpha"), _descriptor("beta")]
    assert select_plugins(plugins, "") == plugins


def test_select_plugins_subset_preserves_discovery_order() -> None:
    plugins = [_descriptor("alpha"), _descriptor("beta"), _descriptor("gamma")]
    selected = select_plugins(plugins, "gamma,alpha")
    assert [plugin.name for plugin in selected] == ["alpha", "gamma"]


def test_select_plugins_accepts_plugin_id_alias() -> None:
    plugin = _descriptor("ai_systems", plugin_id="ai-systems-auditor")
    assert select_plugins([plugin], "ai-systems-auditor") == [plugin]


def test_select_plugins_accepts_underscore_hyphen_alias() -> None:
    plugin = _descriptor("ai_systems")
    assert select_plugins([plugin], "ai-systems") == [plugin]


def test_select_plugins_rejects_unknown_selector() -> None:
    with pytest.raises(ValueError, match="Unknown auditor"):
        select_plugins([_descriptor("alpha")], "missing")


def test_select_plugins_rejects_all_mixed_with_names() -> None:
    with pytest.raises(ValueError, match="cannot be combined"):
        select_plugins([_descriptor("alpha")], "all,alpha")


def test_select_plugins_rejects_duplicate_selectors() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        select_plugins([_descriptor("alpha")], "alpha,alpha")


def test_normalize_output_formats_defaults_alias() -> None:
    assert normalize_output_formats("md,json") == ("markdown", "json")


def test_normalize_output_formats_deduplicates() -> None:
    assert normalize_output_formats("json,json") == ("json",)


def test_normalize_output_formats_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unsupported output"):
        normalize_output_formats("xml")


def test_normalize_output_formats_rejects_empty() -> None:
    with pytest.raises(ValueError, match="At least one"):
        normalize_output_formats(())


def test_normalize_fail_on_accepts_all_severities() -> None:
    assert normalize_fail_on("critical,error,warning,info") == (
        "critical",
        "error",
        "warning",
        "info",
    )


def test_normalize_fail_on_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unsupported severity"):
        normalize_fail_on("fatal")


def test_merge_exclusions_preserves_order_and_case() -> None:
    assert merge_exclusions(["Generated", "cache"], "cache,Build") == [
        "Generated",
        "cache",
        "Build",
    ]


def test_merge_exclusions_rejects_paths() -> None:
    with pytest.raises(ValueError, match="not a path"):
        merge_exclusions("generated/cache")


def test_load_config_missing_file_is_optional(tmp_path: Path) -> None:
    assert load_config(tmp_path / "missing.yaml") == {}


def test_load_config_json(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.json"
    path.write_text(json.dumps({"fail_on": ["error"]}), encoding="utf-8")
    assert load_config(path) == {"fail_on": ["error"]}


def test_load_config_toml(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.toml"
    path.write_text('fail_on = ["critical", "error"]\n', encoding="utf-8")
    assert load_config(path)["fail_on"] == ["critical", "error"]


def test_load_config_yaml_nested_mapping_and_list(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.yaml"
    path.write_text(
        "auditors:\n  alpha:\n    threshold: 7\nexclude:\n  - generated\n",
        encoding="utf-8",
    )
    config = load_config(path)
    assert config["auditors"]["alpha"]["threshold"] == 7
    assert config["exclude"] == ["generated"]


def test_load_config_rejects_unknown_extension(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.ini"
    path.write_text("x=1", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported configuration"):
        load_config(path)


def test_build_plugin_context_merges_defaults_and_specific(tmp_path: Path) -> None:
    plugin = _descriptor(
        "alpha",
        allowed=frozenset(
            {"project_path", "audit_type", "ignored_directories", "threshold"}
        ),
    )
    context = build_plugin_context(
        plugin=plugin,
        project_path=tmp_path,
        config={
            "defaults": {"threshold": 3},
            "auditors": {"alpha": {"threshold": 8}},
        },
        exclusions=["generated"],
    )
    assert context["threshold"] == 8
    assert context["ignored_directories"] == ["generated"]


def test_build_plugin_context_filters_unknown_fields(tmp_path: Path) -> None:
    plugin = _descriptor(
        "alpha",
        allowed=frozenset({"project_path", "audit_type"}),
    )
    context = build_plugin_context(
        plugin=plugin,
        project_path=tmp_path,
        config={"defaults": {"unknown": True}},
        exclusions=[],
    )
    assert "unknown" not in context


def test_build_consolidated_result_clean() -> None:
    consolidated = build_consolidated_result(
        project_path=Path("."),
        audit_results=[_result()],
        started_at=FIXED_STARTED,
        completed_at=FIXED_COMPLETED,
    )
    validate_audit_result(consolidated)
    assert consolidated["plugin_id"] == ORCHESTRATOR_ID
    assert consolidated["status"] == "completed"
    assert consolidated["metrics"]["findings_count"] == 0


def test_build_consolidated_result_flattens_findings_in_order() -> None:
    first = _result(findings=(_finding(FindingSeverity.WARNING),), status=AuditStatus.COMPLETED_WITH_FINDINGS)
    second = _result(
        plugin_id="beta-auditor",
        audit_type="beta",
        findings=(_finding(FindingSeverity.ERROR),),
        status=AuditStatus.COMPLETED_WITH_FINDINGS,
    )
    consolidated = build_consolidated_result(
        project_path=Path("."),
        audit_results=[first, second],
        started_at=FIXED_STARTED,
        completed_at=FIXED_COMPLETED,
    )
    assert [f["severity"] for f in consolidated["findings"]] == ["warning", "error"]
    assert consolidated["summary"]["plugin_ids"] == ["alpha-auditor", "beta-auditor"]


def test_build_consolidated_result_prefixes_execution_errors() -> None:
    failed = _result(status=AuditStatus.FAILED, errors=("boom",))
    consolidated = build_consolidated_result(
        project_path=Path("."),
        audit_results=[failed],
        started_at=FIXED_STARTED,
        completed_at=FIXED_COMPLETED,
    )
    assert consolidated["status"] == "completed_with_errors"
    assert consolidated["errors"] == ["alpha-auditor: boom"]


def test_determine_exit_code_zero_without_matching_findings() -> None:
    result = _result(findings=(_finding(FindingSeverity.WARNING),), status=AuditStatus.COMPLETED_WITH_FINDINGS)
    assert determine_exit_code(audit_results=[result], fail_on=["error"]) == 0


def test_determine_exit_code_one_for_matching_finding() -> None:
    result = _result(findings=(_finding(FindingSeverity.ERROR),), status=AuditStatus.COMPLETED_WITH_FINDINGS)
    assert determine_exit_code(audit_results=[result], fail_on=["error"]) == 1


def test_determine_exit_code_two_for_plugin_failure() -> None:
    failed = _result(status=AuditStatus.FAILED, errors=("boom",))
    assert determine_exit_code(audit_results=[failed], fail_on=[]) == 2


def test_unified_orchestrator_runs_all_plugins_and_writes_reports(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "beta")
    _write_plugin(root, "alpha", severity="warning")
    target = tmp_path / "target"
    target.mkdir()
    result = UnifiedOrchestrator(framework_root=root).run(project_path=target)
    assert [item["audit_type"] for item in result.audit_results] == ["alpha", "beta"]
    assert [path.suffix for path in result.report_paths] == [".md", ".json"]
    assert all(path.is_file() for path in result.report_paths)
    assert isinstance(result.runtime_context, RuntimeContext)


def test_unified_orchestrator_runs_selected_subset(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "alpha")
    _write_plugin(root, "beta")
    target = tmp_path / "target"
    target.mkdir()
    result = UnifiedOrchestrator(framework_root=root).run(
        project_path=target,
        auditors="beta",
        output_formats="json",
    )
    assert [item["audit_type"] for item in result.audit_results] == ["beta"]
    assert len(result.report_paths) == 1


def test_unified_orchestrator_passes_config_and_exclusions(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "alpha")
    target = tmp_path / "target"
    target.mkdir()
    config_path = tmp_path / "uaaf.yaml"
    config_path.write_text(
        "auditors:\n  alpha:\n    threshold: 11\nexclude:\n  - generated\n",
        encoding="utf-8",
    )
    orchestrator = UnifiedOrchestrator(framework_root=root)
    result = orchestrator.run(
        project_path=target,
        config_path=config_path,
        exclude="cache",
        output_formats="json",
    )
    module = orchestrator.discover_plugins()[0].module
    assert result.exit_code == 0
    assert module.LAST_CONTEXT["threshold"] == 11
    assert module.LAST_CONTEXT["ignored_directories"] == ["generated", "cache"]


def test_unified_orchestrator_converts_plugin_exception_and_continues(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "alpha", fail=True)
    _write_plugin(root, "beta")
    target = tmp_path / "target"
    target.mkdir()
    result = UnifiedOrchestrator(framework_root=root).run(
        project_path=target,
        output_formats="json",
    )
    assert len(result.audit_results) == 2
    assert result.audit_results[0]["status"] == "failed"
    assert result.audit_results[1]["status"] == "completed"
    assert result.exit_code == 2


def test_unified_orchestrator_fail_on_matching_severity(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "alpha", severity="critical")
    target = tmp_path / "target"
    target.mkdir()
    result = UnifiedOrchestrator(framework_root=root).run(
        project_path=target,
        fail_on="critical,error",
        output_formats="json",
    )
    assert result.exit_code == 1


def test_unified_orchestrator_rejects_missing_project(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "alpha")
    with pytest.raises(FileNotFoundError, match="project_path"):
        UnifiedOrchestrator(framework_root=root).run(
            project_path=tmp_path / "missing"
        )