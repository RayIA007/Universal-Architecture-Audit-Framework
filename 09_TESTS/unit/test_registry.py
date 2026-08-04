"""Deterministic tests for the canonical dynamic UAAF plugin registry."""

from __future__ import annotations

import os
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

from uaaf_core.orchestrator import UnifiedOrchestrator  # noqa: E402
from uaaf_core.registry import (  # noqa: E402
    DuplicatePluginAliasError,
    DuplicatePluginError,
    NoPluginsDiscoveredError,
    PluginDescriptor,
    PluginDirectoryError,
    PluginImportError,
    PluginMetadataError,
    PluginRunCallableError,
    PluginSelectionError,
    UAAFRegistry,
    UnknownPluginError,
)

FIXED_STARTED = "2026-08-03T12:00:00+00:00"
FIXED_COMPLETED = "2026-08-03T12:00:00.001000+00:00"


def _framework(tmp_path: Path, name: str = "framework") -> Path:
    root = tmp_path / name
    (root / "plugins").mkdir(parents=True)
    (root / "08_SCRIPTS").mkdir(parents=True)
    return root


def _plugin_source(
    name: str,
    *,
    plugin_id: str | None = None,
    audit_type: str | None = None,
    plugin_version: str = "1.0.0",
    plugin_name: str | None = None,
    include_plugin_id: bool = True,
    include_run: bool = True,
    run_value: str = "None",
    extra_source: str = "",
) -> str:
    metadata: list[str] = []
    if include_plugin_id:
        metadata.append(f"PLUGIN_ID = {plugin_id or f'{name}-auditor'!r}")
    metadata.extend(
        [
            f"PLUGIN_VERSION = {plugin_version!r}",
            f"AUDIT_TYPE = {audit_type or name!r}",
        ]
    )
    if plugin_name is not None:
        metadata.append(f"PLUGIN_NAME = {plugin_name!r}")
    metadata.append(
        "_ALLOWED_CONTEXT_FIELDS = {'project_path', 'audit_type', 'threshold'}"
    )
    if include_run:
        metadata.append(
            "def run(context):\n"
            "    global LAST_CONTEXT\n"
            "    LAST_CONTEXT = dict(context)\n"
            f"    return {run_value}\n"
        )
    return "\n".join(metadata) + "\n" + extra_source


def _write_plugin(
    root: Path,
    name: str,
    *,
    source: str | None = None,
    include_init: bool = True,
    include_module: bool = True,
    **source_options: Any,
) -> Path:
    package_dir = root / "plugins" / name
    package_dir.mkdir(parents=True, exist_ok=True)
    if include_init:
        (package_dir / "__init__.py").write_text("", encoding="utf-8")
    if include_module:
        module_source = source or _plugin_source(name, **source_options)
        (package_dir / f"{name}_auditor.py").write_text(
            module_source,
            encoding="utf-8",
        )
    return package_dir


def _valid_result_source(name: str, *, plugin_id: str | None = None) -> str:
    canonical_id = plugin_id or f"{name}-auditor"
    return f'''PLUGIN_ID = {canonical_id!r}
PLUGIN_VERSION = "1.0.0"
AUDIT_TYPE = {name!r}
_ALLOWED_CONTEXT_FIELDS = {{"project_path", "audit_type"}}

def run(context):
    return {{
        "plugin_id": PLUGIN_ID,
        "plugin_version": PLUGIN_VERSION,
        "audit_type": AUDIT_TYPE,
        "status": "completed",
        "summary": {{"project_path": context["project_path"]}},
        "metrics": {{"findings_count": 0}},
        "findings": [],
        "errors": [],
        "execution": {{
            "started_at": {FIXED_STARTED!r},
            "completed_at": {FIXED_COMPLETED!r},
            "duration_ms": 1,
        }},
    }}
'''


def _descriptor(
    name: str,
    *,
    plugin_id: str | None = None,
    audit_type: str | None = None,
    package_root: Path = Path("plugins"),
) -> PluginDescriptor:
    module = ModuleType(f"fixture_{name}_{id(name)}")

    def runner(_context: dict[str, Any]) -> dict[str, Any]:
        return {}

    package_dir = package_root / name
    return PluginDescriptor(
        name=name,
        directory_name=name,
        audit_type=audit_type or name,
        plugin_id=plugin_id or f"{name}-auditor",
        plugin_version="1.0.0",
        package_dir=package_dir,
        module_path=package_dir / f"{name}_auditor.py",
        relative_module_path=(package_dir / f"{name}_auditor.py").as_posix(),
        module_name=module.__name__,
        runner=runner,
        module=module,
    )


# ---------------------------------------------------------------------------
# Basic contract
# ---------------------------------------------------------------------------


def test_empty_registry_has_zero_plugins() -> None:
    registry = UAAFRegistry()
    assert registry.plugin_count == 0
    assert len(registry) == 0


def test_empty_registry_iteration_is_empty() -> None:
    assert list(UAAFRegistry()) == []


def test_empty_registry_lists_no_ids_or_issues() -> None:
    registry = UAAFRegistry()
    assert registry.list_plugins() == ()
    assert registry.list_plugin_ids() == ()
    assert registry.list_discovery_issues() == ()


def test_get_missing_plugin_raises_key_error() -> None:
    with pytest.raises(KeyError, match="not registered"):
        UAAFRegistry().get_plugin("missing-auditor")


def test_has_plugin_is_false_when_missing() -> None:
    assert UAAFRegistry().has_plugin("missing-auditor") is False


def test_clear_plugins_restores_empty_plugin_state() -> None:
    registry = UAAFRegistry()
    registry.register_plugin(_descriptor("alpha"))
    registry.clear_plugins()
    assert registry.plugin_count == 0
    assert registry.list_plugin_ids() == ()


# ---------------------------------------------------------------------------
# Discovery and structure
# ---------------------------------------------------------------------------


def test_discover_valid_plugin(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "alpha")
    registry = UAAFRegistry(framework_root=root)
    discovered = registry.discover_plugins()
    assert [plugin.directory_name for plugin in discovered] == ["alpha"]


def test_discover_rejects_missing_framework_directory(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    registry = UAAFRegistry(framework_root=missing)
    with pytest.raises(PluginDirectoryError, match="framework_root does not exist"):
        registry.discover_plugins()


def test_discover_rejects_missing_plugins_directory(tmp_path: Path) -> None:
    root = tmp_path / "framework"
    root.mkdir()
    registry = UAAFRegistry(framework_root=root)
    with pytest.raises(PluginDirectoryError, match="plugins_dir does not exist"):
        registry.discover_plugins()


def test_discover_empty_directory_raises_specific_error(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    with pytest.raises(NoPluginsDiscoveredError, match="No auditor plugins"):
        UAAFRegistry(framework_root=root).discover_plugins()


def test_discovery_order_is_alphabetical_and_deterministic(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "zeta")
    _write_plugin(root, "Alpha", audit_type="alpha", plugin_id="alpha-auditor")
    _write_plugin(root, "beta")
    names = [
        plugin.directory_name
        for plugin in UAAFRegistry(framework_root=root).discover_plugins()
    ]
    assert names == ["Alpha", "beta", "zeta"]


def test_discovery_ignores_hidden_directory(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, ".hidden")
    _write_plugin(root, "visible")
    plugins = UAAFRegistry(framework_root=root).discover_plugins()
    assert [plugin.directory_name for plugin in plugins] == ["visible"]


def test_discovery_ignores_pycache_directory(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "__pycache__")
    _write_plugin(root, "valid")
    plugins = UAAFRegistry(framework_root=root).discover_plugins()
    assert [plugin.directory_name for plugin in plugins] == ["valid"]


def test_discovery_ignores_loose_files(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    (root / "plugins" / "loose.py").write_text("raise RuntimeError", encoding="utf-8")
    _write_plugin(root, "valid")
    plugins = UAAFRegistry(framework_root=root).discover_plugins()
    assert [plugin.directory_name for plugin in plugins] == ["valid"]


def test_plugin_without_init_is_isolated_and_reported(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "broken", include_init=False)
    _write_plugin(root, "valid")
    registry = UAAFRegistry(framework_root=root)
    plugins = registry.discover_plugins()
    assert [plugin.directory_name for plugin in plugins] == ["valid"]
    issue = registry.list_discovery_issues()[0]
    assert issue.code == "invalid_structure"
    assert "__init__.py" in issue.message


def test_plugin_without_auditor_module_is_isolated_and_reported(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "broken", include_module=False)
    _write_plugin(root, "valid")
    registry = UAAFRegistry(framework_root=root)
    registry.discover_plugins()
    issue = registry.list_discovery_issues()[0]
    assert "broken_auditor.py" in issue.message


def test_discovery_supports_paths_with_spaces(tmp_path: Path) -> None:
    root = _framework(tmp_path, "framework with spaces")
    _write_plugin(root, "alpha")
    plugin = UAAFRegistry(framework_root=root).discover_plugins()[0]
    assert "framework with spaces" in str(plugin.module_path)


def test_discovered_stable_path_uses_posix_separators(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "alpha")
    plugin = UAAFRegistry(framework_root=root).discover_plugins()[0]
    assert plugin.relative_module_path == "plugins/alpha/alpha_auditor.py"
    assert "\\" not in plugin.relative_module_path


# ---------------------------------------------------------------------------
# Import and validation
# ---------------------------------------------------------------------------


def test_syntax_error_is_wrapped_as_plugin_import_error(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "broken", source="def invalid(:\n")
    with pytest.raises(PluginImportError, match="SyntaxError"):
        UAAFRegistry(framework_root=root).discover_plugins()


def test_import_error_is_wrapped_as_plugin_import_error(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    source = _plugin_source("broken", extra_source="import package_that_does_not_exist_uaaf\n")
    _write_plugin(root, "broken", source=source)
    registry = UAAFRegistry(framework_root=root)
    with pytest.raises(PluginImportError, match="ModuleNotFoundError"):
        registry.discover_plugins()
    assert registry.list_discovery_issues()[0].code == "import_error"


def test_missing_run_is_rejected(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "broken", include_run=False)
    with pytest.raises(PluginRunCallableError, match="callable run"):
        UAAFRegistry(framework_root=root).discover_plugins()


def test_non_callable_run_is_rejected(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "broken", source=_plugin_source("broken", include_run=False) + "run = 42\n")
    with pytest.raises(PluginRunCallableError, match="callable run"):
        UAAFRegistry(framework_root=root).discover_plugins()


def test_missing_plugin_id_is_rejected(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "broken", include_plugin_id=False)
    with pytest.raises(PluginMetadataError, match="PLUGIN_ID must be defined"):
        UAAFRegistry(framework_root=root).discover_plugins()


def test_empty_plugin_id_is_rejected(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "broken", plugin_id=" ")
    with pytest.raises(PluginMetadataError, match="PLUGIN_ID must be a non-empty"):
        UAAFRegistry(framework_root=root).discover_plugins()


def test_discovery_restores_sys_path(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "alpha")
    before = list(sys.path)
    UAAFRegistry(framework_root=root).discover_plugins()
    assert sys.path == before


def test_registration_does_not_execute_public_run(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    source = '''PLUGIN_ID = "alpha-auditor"
PLUGIN_VERSION = "1.0.0"
AUDIT_TYPE = "alpha"
RUN_COUNT = 0
def run(context):
    global RUN_COUNT
    RUN_COUNT += 1
    return context
'''
    _write_plugin(root, "alpha", source=source)
    plugin = UAAFRegistry(framework_root=root).discover_plugins()[0]
    assert plugin.module.RUN_COUNT == 0


def test_clear_plugins_removes_owned_dynamic_modules(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "alpha")
    registry = UAAFRegistry(framework_root=root)
    plugin = registry.discover_plugins()[0]
    package_name = plugin.module_name.rsplit(".", 1)[0]
    assert plugin.module_name in sys.modules
    assert package_name in sys.modules
    registry.clear_plugins()
    assert plugin.module_name not in sys.modules
    assert package_name not in sys.modules


def test_repeated_discovery_reuses_unchanged_module(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "alpha")
    registry = UAAFRegistry(framework_root=root)
    first = registry.discover_plugins()[0]
    second = registry.discover_plugins()[0]
    assert first.module is second.module
    assert first.runner is second.runner


def test_changed_module_is_reimported(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    package = _write_plugin(root, "alpha", plugin_version="1.0.0")
    registry = UAAFRegistry(framework_root=root)
    first = registry.discover_plugins()[0]
    module_path = package / "alpha_auditor.py"
    module_path.write_text(
        _plugin_source("alpha", plugin_version="2.0.0") + "# changed-size\n",
        encoding="utf-8",
    )
    stat = module_path.stat()
    os.utime(module_path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))
    second = registry.discover_plugins()[0]
    assert second.plugin_version == "2.0.0"
    assert second.module is not first.module


def test_same_plugin_name_in_different_roots_is_isolated(tmp_path: Path) -> None:
    first_root = _framework(tmp_path, "first")
    second_root = _framework(tmp_path, "second")
    _write_plugin(first_root, "alpha", plugin_id="first-auditor")
    _write_plugin(second_root, "alpha", plugin_id="second-auditor")
    first = UAAFRegistry(framework_root=first_root).discover_plugins()[0]
    second = UAAFRegistry(framework_root=second_root).discover_plugins()[0]
    assert first.module_name != second.module_name
    assert first.plugin_id == "first-auditor"
    assert second.plugin_id == "second-auditor"


def test_relative_imports_inside_plugin_package_are_supported(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    package = _write_plugin(
        root,
        "relative",
        source='''from .helper import PLUGIN_ID_VALUE
PLUGIN_ID = PLUGIN_ID_VALUE
PLUGIN_VERSION = "1.0.0"
AUDIT_TYPE = "relative"
def run(context):
    return context
''',
    )
    (package / "helper.py").write_text(
        'PLUGIN_ID_VALUE = "relative-auditor"\n',
        encoding="utf-8",
    )
    plugin = UAAFRegistry(framework_root=root).discover_plugins()[0]
    assert plugin.plugin_id == "relative-auditor"


def test_package_init_may_import_auditor_without_double_execution(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    package = _write_plugin(
        root,
        "alpha",
        source='''from .counter import COUNTER
COUNTER.append("imported")
PLUGIN_ID = "alpha-auditor"
PLUGIN_VERSION = "1.0.0"
AUDIT_TYPE = "alpha"
def run(context):
    return context
''',
    )
    (package / "counter.py").write_text("COUNTER = []\n", encoding="utf-8")
    (package / "__init__.py").write_text(
        "from .alpha_auditor import run\n",
        encoding="utf-8",
    )
    plugin = UAAFRegistry(framework_root=root).discover_plugins()[0]
    assert plugin.module.COUNTER == ["imported"]


# ---------------------------------------------------------------------------
# Registration, metadata, lookup, and selection
# ---------------------------------------------------------------------------


def test_register_valid_descriptor() -> None:
    registry = UAAFRegistry()
    plugin = _descriptor("alpha")
    assert registry.register_plugin(plugin) is plugin
    assert registry.plugin_count == 1


def test_register_same_descriptor_is_idempotent() -> None:
    registry = UAAFRegistry()
    plugin = _descriptor("alpha")
    registry.register_plugin(plugin)
    assert registry.register_plugin(plugin) is plugin
    assert registry.plugin_count == 1


def test_duplicate_plugin_id_from_different_descriptors_is_rejected() -> None:
    registry = UAAFRegistry()
    registry.register_plugin(_descriptor("alpha", plugin_id="same-auditor"))
    with pytest.raises(DuplicatePluginError, match="Duplicate plugin identifier"):
        registry.register_plugin(_descriptor("beta", plugin_id="same-auditor"))


def test_register_replace_updates_duplicate_plugin_id() -> None:
    registry = UAAFRegistry()
    first = _descriptor("alpha", plugin_id="same-auditor")
    replacement = _descriptor("beta", plugin_id="same-auditor")
    registry.register_plugin(first)
    registry.register_plugin(replacement, replace=True)
    assert registry.get_plugin("same-auditor") is replacement


def test_unregister_plugin_removes_it() -> None:
    registry = UAAFRegistry()
    registry.register_plugin(_descriptor("alpha"))
    registry.unregister_plugin("alpha-auditor")
    assert registry.has_plugin("alpha-auditor") is False


def test_manual_registration_order_is_deterministic() -> None:
    registry = UAAFRegistry()
    registry.register_plugin(_descriptor("zeta"))
    registry.register_plugin(_descriptor("alpha"))
    assert registry.list_plugin_ids() == ("alpha-auditor", "zeta-auditor")


def test_discovered_descriptor_exposes_canonical_metadata(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(
        root,
        "alpha",
        plugin_id="custom-auditor",
        audit_type="custom-type",
        plugin_version="3.2.1",
        plugin_name="Custom Alpha",
    )
    plugin = UAAFRegistry(framework_root=root).discover_plugins()[0]
    assert plugin.name == "Custom Alpha"
    assert plugin.directory_name == "alpha"
    assert plugin.version == "3.2.1"
    assert plugin.run is plugin.runner
    assert plugin.metadata["PLUGIN_ID"] == "custom-auditor"
    assert plugin.validation_status == "registered"


def test_get_and_has_plugin_use_canonical_id() -> None:
    registry = UAAFRegistry()
    plugin = _descriptor("alpha")
    registry.register_plugin(plugin)
    assert registry.has_plugin("alpha-auditor") is True
    assert registry.get_plugin("alpha-auditor") is plugin


def test_resolve_plugin_accepts_directory_audit_type_and_plugin_id() -> None:
    registry = UAAFRegistry()
    plugin = _descriptor("ai_systems", plugin_id="ai-systems-auditor", audit_type="ai-systems")
    registry.register_plugin(plugin)
    assert registry.resolve_plugin("ai_systems") is plugin
    assert registry.resolve_plugin("ai-systems") is plugin
    assert registry.resolve_plugin("ai-systems-auditor") is plugin


def test_select_all_uses_canonical_order() -> None:
    registry = UAAFRegistry()
    registry.register_plugin(_descriptor("zeta"))
    registry.register_plugin(_descriptor("alpha"))
    assert [plugin.directory_name for plugin in registry.select_plugins("all")] == [
        "alpha",
        "zeta",
    ]


def test_select_subset_uses_canonical_order() -> None:
    registry = UAAFRegistry()
    for name in ("alpha", "beta", "gamma"):
        registry.register_plugin(_descriptor(name))
    selected = registry.select_plugins("gamma,alpha")
    assert [plugin.directory_name for plugin in selected] == ["alpha", "gamma"]


def test_select_subset_deduplicates_selectors() -> None:
    registry = UAAFRegistry()
    registry.register_plugin(_descriptor("alpha"))
    assert registry.select_plugins("alpha,alpha") == registry.select_plugins("alpha")


def test_select_unknown_plugin_raises_specific_error() -> None:
    registry = UAAFRegistry()
    registry.register_plugin(_descriptor("alpha"))
    with pytest.raises(UnknownPluginError, match="Unknown auditor selector"):
        registry.select_plugins("missing")


def test_select_all_cannot_be_combined_with_subset() -> None:
    registry = UAAFRegistry()
    registry.register_plugin(_descriptor("alpha"))
    with pytest.raises(PluginSelectionError, match="cannot be combined"):
        registry.select_plugins("all,alpha")


def test_find_unknown_selectors_is_non_throwing() -> None:
    registry = UAAFRegistry()
    registry.register_plugin(_descriptor("alpha"))
    assert registry.find_unknown_selectors("alpha,missing,other") == (
        "missing",
        "other",
    )


def test_ambiguous_alias_is_rejected() -> None:
    registry = UAAFRegistry()
    registry.register_plugin(
        _descriptor("alpha", plugin_id="first-auditor", audit_type="shared")
    )
    with pytest.raises(DuplicatePluginAliasError, match="Ambiguous plugin selector"):
        registry.register_plugin(
            _descriptor("beta", plugin_id="second-auditor", audit_type="shared")
        )


def test_failed_discovery_preserves_previous_registered_plugins(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    package = _write_plugin(root, "alpha")
    registry = UAAFRegistry(framework_root=root)
    first = registry.discover_plugins()
    (package / "alpha_auditor.py").write_text("def invalid(:\n", encoding="utf-8")
    with pytest.raises(PluginImportError):
        registry.discover_plugins()
    assert registry.list_plugin_ids() == ("alpha-auditor",)
    assert registry.list_plugins()[0].module is first[0].module


def test_snapshot_preserves_original_component_shape() -> None:
    registry = UAAFRegistry()
    registry.register_plugin(_descriptor("alpha"))
    assert registry.snapshot() == {
        "processor_count": 0,
        "profile_count": 0,
        "processors": {},
        "profiles": {},
    }


def test_plugin_snapshot_contains_plugin_summary() -> None:
    registry = UAAFRegistry()
    registry.register_plugin(_descriptor("alpha"))
    snapshot = registry.plugin_snapshot()
    assert snapshot["plugin_count"] == 1
    assert snapshot["plugins"]["alpha-auditor"]["audit_type"] == "alpha"


def test_clear_removes_processors_profiles_and_plugins() -> None:
    registry = UAAFRegistry()
    registry.register_plugin(_descriptor("alpha"))
    registry.clear()
    assert registry.is_empty is True
    assert registry.plugin_snapshot()["plugin_count"] == 0


# ---------------------------------------------------------------------------
# Orchestrator and real-plugin integration
# ---------------------------------------------------------------------------


def test_orchestrator_delegates_discovery_to_injected_registry(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    plugin = _descriptor("alpha", package_root=root / "plugins")

    class FakeRegistry:
        framework_root = root
        plugins_dir = root / "plugins"

        def __init__(self) -> None:
            self.discovery_calls: list[tuple[Path, Path]] = []

        def discover_plugins(self, *, framework_root: Path, plugins_dir: Path):
            self.discovery_calls.append((framework_root, plugins_dir))
            return (plugin,)

    fake = FakeRegistry()
    orchestrator = UnifiedOrchestrator(registry=fake)  # type: ignore[arg-type]
    assert orchestrator.discover_plugins() == [plugin]
    assert fake.discovery_calls == [(root.resolve(), (root / "plugins").resolve())]


def test_orchestrator_uses_registry_selection_for_subset(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "alpha", source=_valid_result_source("alpha"))
    _write_plugin(root, "beta", source=_valid_result_source("beta"))
    registry = UAAFRegistry(framework_root=root)
    orchestrator = UnifiedOrchestrator(registry=registry)
    result = orchestrator.run(
        project_path=root,
        auditors="beta",
        output_formats="json",
        output_dir=root / "outputs",
    )
    assert [item["plugin_id"] for item in result.audit_results] == ["beta-auditor"]


def test_orchestrator_reuses_canonical_registry_for_runtime_components(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "alpha", source=_valid_result_source("alpha"))
    registry = UAAFRegistry(framework_root=root)
    UnifiedOrchestrator(registry=registry).run(
        project_path=root,
        auditors="all",
        output_formats="json",
        output_dir=root / "outputs",
    )
    assert registry.has_plugin("alpha-auditor")
    assert registry.has_processor("alpha-auditor")
    assert registry.has_profile("uaaf-unified-cli")


def test_two_realistic_plugins_discover_and_execute_in_order(tmp_path: Path) -> None:
    root = _framework(tmp_path)
    _write_plugin(root, "zeta", source=_valid_result_source("zeta"))
    _write_plugin(root, "alpha", source=_valid_result_source("alpha"))
    result = UnifiedOrchestrator(framework_root=root).run(
        project_path=root,
        auditors="all",
        output_formats="json",
        output_dir=root / "outputs",
    )
    assert [item["plugin_id"] for item in result.audit_results] == [
        "alpha-auditor",
        "zeta-auditor",
    ]


def test_current_repository_discovers_five_supported_plugins() -> None:
    expected = {
        "architecture-auditor",
        "testing-auditor",
        "configuration-auditor",
        "documentation-auditor",
        "ai-systems-auditor",
    }
    registry = UAAFRegistry(
        framework_root=PROJECT_ROOT,
        plugins_dir=PROJECT_ROOT / "plugins",
    )
    assert set(registry.discover_plugins())
    assert set(registry.list_plugin_ids()) == expected
