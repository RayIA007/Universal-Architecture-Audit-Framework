"""Deterministic tests for UAAF canonical global configuration."""

from __future__ import annotations

import json
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "08_SCRIPTS"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from uaaf_core.config import (  # noqa: E402
    ConfigConflictError,
    ConfigFileError,
    ConfigOverrides,
    ConfigValidationError,
    DEFAULT_OUTPUT_FORMATS,
    ResolvedConfig,
    UNSET,
    collect_explicit_cli_fields,
    load_config,
    load_config_file,
    merge_exclusions,
    normalize_auditors,
    normalize_fail_on,
    normalize_output_formats,
    overrides_from_cli,
    overrides_from_mapping,
    resolve_global_config,
)


@pytest.fixture
def framework(tmp_path: Path) -> Path:
    root = tmp_path / "framework with spaces"
    (root / "plugins").mkdir(parents=True)
    return root


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "project with spaces"
    path.mkdir()
    return path


def test_unset_has_stable_representation() -> None:
    assert repr(UNSET) == "UNSET"


def test_config_overrides_reports_only_supplied_fields() -> None:
    overrides = ConfigOverrides(auditors=("all",), fail_on=())
    assert overrides.supplied_fields() == ("auditors", "fail_on")


def test_config_overrides_distinguishes_unset_from_none() -> None:
    overrides = ConfigOverrides(output_dir=None)
    assert overrides.output_dir is None
    assert overrides.project_path is UNSET


def test_collect_explicit_cli_fields_supports_separate_values() -> None:
    assert collect_explicit_cli_fields(
        ["--project-path", "target", "--exclude", "build"]
    ) == frozenset({"project_path", "exclude"})


def test_collect_explicit_cli_fields_supports_equals_syntax() -> None:
    assert collect_explicit_cli_fields(
        ["--output-formats=json", "--fail-on=error"]
    ) == frozenset({"output_formats", "fail_on"})


def test_collect_explicit_cli_fields_ignores_values() -> None:
    assert collect_explicit_cli_fields(
        ["--project-path", "--not-an-option-value"]
    ) == frozenset({"project_path"})


def test_normalize_auditors_casefolds_and_deduplicates() -> None:
    assert normalize_auditors("Architecture, testing,ARCHITECTURE") == (
        "architecture",
        "testing",
    )


def test_normalize_auditors_rejects_empty() -> None:
    with pytest.raises(ConfigValidationError, match="At least one auditor"):
        normalize_auditors([])


def test_normalize_auditors_rejects_all_combination() -> None:
    with pytest.raises(ConfigValidationError, match="cannot be combined"):
        normalize_auditors("all,architecture")


def test_normalize_output_formats_accepts_md_alias() -> None:
    assert normalize_output_formats("md,json") == ("markdown", "json")


def test_normalize_output_formats_deduplicates_in_first_seen_order() -> None:
    assert normalize_output_formats(["json", "MARKDOWN", "json"]) == (
        "json",
        "markdown",
    )


def test_normalize_output_formats_rejects_unknown() -> None:
    with pytest.raises(ConfigValidationError, match="Unsupported output"):
        normalize_output_formats("xml")


def test_normalize_output_formats_rejects_empty() -> None:
    with pytest.raises(ConfigValidationError, match="At least one output"):
        normalize_output_formats([])


def test_normalize_fail_on_accepts_empty() -> None:
    assert normalize_fail_on(()) == ()


def test_normalize_fail_on_casefolds_and_deduplicates() -> None:
    assert normalize_fail_on("CRITICAL,error,critical") == (
        "critical",
        "error",
    )


def test_normalize_fail_on_rejects_unknown() -> None:
    with pytest.raises(ConfigValidationError, match="Unsupported severity"):
        normalize_fail_on("fatal")


def test_merge_exclusions_preserves_order_and_case() -> None:
    assert merge_exclusions("Generated,cache", ["cache", "Build"]) == [
        "Generated",
        "cache",
        "Build",
    ]


def test_merge_exclusions_ignores_empty_entries() -> None:
    assert merge_exclusions("generated,, ", ["", "cache"]) == [
        "generated",
        "cache",
    ]


@pytest.mark.parametrize("value", ["generated/cache", "generated\\cache", ".", ".."])
def test_merge_exclusions_rejects_paths(value: str) -> None:
    with pytest.raises(ConfigValidationError, match="not a path"):
        merge_exclusions(value)


def test_merge_exclusions_rejects_non_string_items() -> None:
    with pytest.raises(ConfigValidationError, match="only strings"):
        merge_exclusions(["cache", 7])


def test_load_config_none_returns_empty_mapping() -> None:
    loaded = load_config_file(None)
    assert loaded.path is None
    assert loaded.data == {}
    assert isinstance(loaded.data, MappingProxyType)


def test_load_config_missing_file_is_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigFileError, match="does not exist"):
        load_config_file(tmp_path / "missing.yaml")


def test_load_config_directory_is_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigFileError, match="regular file"):
        load_config_file(tmp_path)


def test_load_config_rejects_unknown_extension(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.ini"
    path.write_text("x=1", encoding="utf-8")
    with pytest.raises(ConfigFileError, match="Unsupported configuration"):
        load_config_file(path)


def test_load_config_json(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.json"
    path.write_text(json.dumps({"fail_on": ["error"]}), encoding="utf-8")
    assert load_config(path) == {"fail_on": ["error"]}


def test_load_config_empty_json(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.json"
    path.write_text("", encoding="utf-8")
    assert load_config(path) == {}


def test_load_config_invalid_json_has_stable_error(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ConfigFileError, match="Invalid JSON configuration syntax"):
        load_config(path)


def test_load_config_json_root_must_be_mapping(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ConfigValidationError, match="root must be a mapping"):
        load_config(path)


def test_load_config_toml(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.toml"
    path.write_text('fail_on = ["critical", "error"]\n', encoding="utf-8")
    assert load_config(path)["fail_on"] == ["critical", "error"]


def test_load_config_invalid_toml_has_stable_error(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.toml"
    path.write_text("fail_on = [", encoding="utf-8")
    with pytest.raises(ConfigFileError, match="Invalid TOML configuration syntax"):
        load_config(path)


def test_load_config_supports_tool_uaaf_toml(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"
    path.write_text(
        '[project]\nname = "sample"\n\n[tool.uaaf]\noutput_formats = ["json"]\n',
        encoding="utf-8",
    )
    assert load_config(path) == {"output_formats": ["json"]}


def test_load_config_rejects_direct_fields_with_tool_uaaf(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"
    path.write_text(
        'output_formats = ["markdown"]\n[tool.uaaf]\noutput_formats = ["json"]\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigConflictError, match="cannot combine"):
        load_config(path)


def test_load_config_yaml_nested_mapping_and_list(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.yaml"
    path.write_text(
        "plugins:\n  alpha:\n    threshold: 7\nexclude:\n  - generated\n",
        encoding="utf-8",
    )
    config = load_config(path)
    assert config["plugins"]["alpha"]["threshold"] == 7
    assert config["exclude"] == ["generated"]


def test_load_config_yml_extension(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.yml"
    path.write_text("output_formats: [json]\n", encoding="utf-8")
    assert load_config(path)["output_formats"] == ["json"]


def test_load_config_empty_yaml(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.yaml"
    path.write_text("# only a comment\n", encoding="utf-8")
    assert load_config(path) == {}


def test_load_config_yaml_rejects_tabs(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.yaml"
    path.write_text("plugins:\n\talpha: {}\n", encoding="utf-8")
    with pytest.raises(ConfigFileError, match="spaces, not tabs"):
        load_config(path)


def test_load_config_yaml_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.yaml"
    path.write_text("fail_on: error\nfail_on: warning\n", encoding="utf-8")
    with pytest.raises(ConfigFileError, match="Duplicate YAML key"):
        load_config(path)


def test_load_config_yaml_rejects_list_of_mappings(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.yaml"
    path.write_text("items:\n  - name: alpha\n", encoding="utf-8")
    with pytest.raises(ConfigFileError, match="list items are not supported"):
        load_config(path)


def test_load_config_rejects_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "uaaf.json"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(ConfigFileError, match="not valid UTF-8"):
        load_config(path)


def test_overrides_from_mapping_rejects_unknown_fields(tmp_path: Path) -> None:
    with pytest.raises(ConfigValidationError, match="Unknown global"):
        overrides_from_mapping({"outpt_formats": ["json"]}, base_dir=tmp_path)


def test_overrides_from_mapping_supports_auditors_selection(tmp_path: Path) -> None:
    overrides = overrides_from_mapping(
        {"auditors": ["architecture", "testing"]},
        base_dir=tmp_path,
    )
    assert overrides.auditors == ("architecture", "testing")
    assert overrides.plugin_configs is UNSET


def test_overrides_from_mapping_supports_historical_auditors_sections(
    tmp_path: Path,
) -> None:
    overrides = overrides_from_mapping(
        {"auditors": {"architecture": {"max_complexity": 8}}},
        base_dir=tmp_path,
    )
    assert overrides.auditors is UNSET
    assert overrides.plugin_configs == {
        "architecture": {"max_complexity": 8}
    }


def test_overrides_from_mapping_rejects_plugin_alias_conflict(tmp_path: Path) -> None:
    with pytest.raises(ConfigConflictError, match="conflicting plugin sections"):
        overrides_from_mapping(
            {
                "plugins": {"architecture": {"max_complexity": 8}},
                "auditors": {"architecture": {"max_complexity": 9}},
            },
            base_dir=tmp_path,
        )


def test_overrides_from_mapping_accepts_equal_default_aliases(tmp_path: Path) -> None:
    overrides = overrides_from_mapping(
        {"defaults": {"enabled": False}, "global": {"enabled": False}},
        base_dir=tmp_path,
    )
    assert overrides.plugin_defaults == {"enabled": False}


def test_overrides_from_mapping_rejects_default_alias_conflict(tmp_path: Path) -> None:
    with pytest.raises(ConfigConflictError, match="defaults.*global"):
        overrides_from_mapping(
            {"defaults": {"enabled": False}, "global": {"enabled": True}},
            base_dir=tmp_path,
        )


def test_overrides_from_mapping_requires_plugin_sections_mapping(tmp_path: Path) -> None:
    with pytest.raises(ConfigValidationError, match="plugins.*mapping"):
        overrides_from_mapping({"plugins": []}, base_dir=tmp_path)


def test_overrides_from_mapping_requires_individual_plugin_mapping(tmp_path: Path) -> None:
    with pytest.raises(ConfigValidationError, match="plugin 'alpha'.*mapping"):
        overrides_from_mapping({"plugins": {"alpha": 7}}, base_dir=tmp_path)


def test_overrides_from_cli_ignores_parser_defaults_not_explicit(tmp_path: Path) -> None:
    overrides = overrides_from_cli(
        {
            "project_path": ".",
            "auditors": "all",
            "output_formats": DEFAULT_OUTPUT_FORMATS,
        },
        explicit_fields=(),
        base_dir=tmp_path,
    )
    assert overrides.supplied_fields() == ()


def test_overrides_from_cli_preserves_explicit_empty_fail_on(tmp_path: Path) -> None:
    overrides = overrides_from_cli(
        {"fail_on": ()},
        explicit_fields={"fail_on"},
        base_dir=tmp_path,
    )
    assert overrides.fail_on == ()


def test_resolve_defaults(
    framework: Path,
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(project)
    config = resolve_global_config(framework_root_default=framework)
    assert config.project_path == project.resolve()
    assert config.auditors == ("all",)
    assert config.output_formats == ("markdown", "json")
    assert config.fail_on == ()
    assert config.exclude == ()
    assert config.framework_root == framework.resolve()
    assert config.plugins_dir == (framework / "plugins").resolve()
    assert config.output_dir == (framework / "07_OUTPUTS").resolve()


def test_resolve_file_overrides_defaults(framework: Path, project: Path) -> None:
    config_path = framework / "uaaf.json"
    config_path.write_text(
        json.dumps(
            {
                "project_path": str(project),
                "auditors": ["testing"],
                "output_formats": ["json"],
                "fail_on": ["error"],
                "exclude": ["build"],
            }
        ),
        encoding="utf-8",
    )
    config = resolve_global_config(
        config_path=config_path,
        framework_root_default=framework,
    )
    assert config.project_path == project.resolve()
    assert config.auditors == ("testing",)
    assert config.output_formats == ("json",)
    assert config.fail_on == ("error",)
    assert config.exclude == ("build",)


def test_resolve_cli_explicit_overrides_file(framework: Path, project: Path) -> None:
    other_project = framework / "other project"
    other_project.mkdir()
    config_path = framework / "uaaf.toml"
    config_path.write_text(
        f'project_path = {str(project)!r}\noutput_formats = ["markdown"]\nfail_on = ["warning"]\n',
        encoding="utf-8",
    )
    config = resolve_global_config(
        cli_values={
            "project_path": str(other_project),
            "output_formats": ("json",),
            "fail_on": (),
        },
        explicit_cli_fields={"project_path", "output_formats", "fail_on"},
        config_path=config_path,
        framework_root_default=framework,
    )
    assert config.project_path == other_project.resolve()
    assert config.output_formats == ("json",)
    assert config.fail_on == ()


def test_resolve_absent_cli_preserves_file(framework: Path, project: Path) -> None:
    config_path = framework / "uaaf.json"
    config_path.write_text(
        json.dumps(
            {
                "project_path": str(project),
                "output_formats": ["json"],
            }
        ),
        encoding="utf-8",
    )
    config = resolve_global_config(
        cli_values={"project_path": ".", "output_formats": DEFAULT_OUTPUT_FORMATS},
        explicit_cli_fields=(),
        config_path=config_path,
        framework_root_default=framework,
    )
    assert config.project_path == project.resolve()
    assert config.output_formats == ("json",)


def test_resolve_merges_file_and_cli_exclusions(framework: Path, project: Path) -> None:
    config_path = framework / "uaaf.json"
    config_path.write_text(
        json.dumps({"project_path": str(project), "exclude": ["build", "cache"]}),
        encoding="utf-8",
    )
    config = resolve_global_config(
        cli_values={"exclude": ["cache", "Generated"]},
        explicit_cli_fields={"exclude"},
        config_path=config_path,
        framework_root_default=framework,
    )
    assert config.exclude == ("build", "cache", "Generated")


def test_file_relative_paths_resolve_against_config_directory(
    framework: Path,
) -> None:
    config_dir = framework / "config files"
    project = config_dir / "relative project"
    plugins = config_dir / "relative plugins"
    project.mkdir(parents=True)
    plugins.mkdir()
    path = config_dir / "uaaf.json"
    path.write_text(
        json.dumps(
            {
                "project_path": "relative project",
                "plugins_dir": "relative plugins",
                "output_dir": "relative reports",
            }
        ),
        encoding="utf-8",
    )
    config = resolve_global_config(
        config_path=path,
        framework_root_default=framework,
    )
    assert config.project_path == project.resolve()
    assert config.plugins_dir == plugins.resolve()
    assert config.output_dir == (config_dir / "relative reports").resolve()


def test_cli_relative_paths_resolve_against_cwd(framework: Path, project: Path) -> None:
    cwd = project.parent
    config = resolve_global_config(
        cli_values={"project_path": project.name},
        explicit_cli_fields={"project_path"},
        cwd=cwd,
        framework_root_default=framework,
    )
    assert config.project_path == project.resolve()


def test_resolve_rejects_missing_project(framework: Path, tmp_path: Path) -> None:
    with pytest.raises(ConfigValidationError, match="project_path does not exist"):
        resolve_global_config(
            cli_values={"project_path": str(tmp_path / "missing")},
            explicit_cli_fields={"project_path"},
            framework_root_default=framework,
        )


def test_resolve_rejects_file_as_plugins_dir(
    framework: Path,
    project: Path,
) -> None:
    file_path = framework / "not-plugins"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(ConfigValidationError, match="plugins_dir is not a directory"):
        resolve_global_config(
            cli_values={
                "project_path": str(project),
                "plugins_dir": str(file_path),
            },
            explicit_cli_fields={"project_path", "plugins_dir"},
            framework_root_default=framework,
        )


def test_output_dir_may_not_exist(framework: Path, project: Path) -> None:
    output = framework / "new reports"
    config = resolve_global_config(
        cli_values={"project_path": str(project), "output_dir": str(output)},
        explicit_cli_fields={"project_path", "output_dir"},
        framework_root_default=framework,
    )
    assert config.output_dir == output.resolve()
    assert not output.exists()


def test_resolved_config_is_frozen(framework: Path, project: Path) -> None:
    config = resolve_global_config(
        cli_values={"project_path": str(project)},
        explicit_cli_fields={"project_path"},
        framework_root_default=framework,
    )
    with pytest.raises(FrozenInstanceError):
        config.project_path = framework  # type: ignore[misc]


def test_resolved_config_nested_mappings_are_immutable(
    framework: Path,
    project: Path,
) -> None:
    config_path = framework / "uaaf.json"
    config_path.write_text(
        json.dumps(
            {
                "project_path": str(project),
                "plugins": {"alpha": {"nested": {"enabled": False}}},
            }
        ),
        encoding="utf-8",
    )
    config = resolve_global_config(
        config_path=config_path,
        framework_root_default=framework,
    )
    with pytest.raises(TypeError):
        config.plugin_configs["alpha"]["nested"] = {}  # type: ignore[index]
    nested = config.plugin_configs["alpha"]["nested"]
    assert isinstance(nested, MappingProxyType)


def test_resolved_config_has_no_shared_mutable_state(
    framework: Path,
    project: Path,
) -> None:
    first = resolve_global_config(
        cli_values={"project_path": str(project)},
        explicit_cli_fields={"project_path"},
        framework_root_default=framework,
    )
    second = resolve_global_config(
        cli_values={"project_path": str(project)},
        explicit_cli_fields={"project_path"},
        framework_root_default=framework,
    )
    assert first.plugin_defaults is not second.plugin_defaults
    assert first.plugin_configs is not second.plugin_configs


def test_plugin_source_mapping_is_defensive(framework: Path, project: Path) -> None:
    path = framework / "uaaf.json"
    path.write_text(
        json.dumps(
            {
                "project_path": str(project),
                "plugins": {"alpha": {"threshold": 7}},
            }
        ),
        encoding="utf-8",
    )
    config = resolve_global_config(
        config_path=path,
        framework_root_default=framework,
    )
    source = config.plugin_source_mapping()
    source["plugins"]["alpha"]["threshold"] = 99
    assert config.plugin_configs["alpha"]["threshold"] == 7


def test_safe_snapshot_redacts_sensitive_keys(framework: Path, project: Path) -> None:
    path = framework / "uaaf.json"
    path.write_text(
        json.dumps(
            {
                "project_path": str(project),
                "plugins": {
                    "alpha": {
                        "api_key": "secret-value",
                        "nested": {"access_token": "token-value"},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    config = resolve_global_config(
        config_path=path,
        framework_root_default=framework,
    )
    snapshot = config.to_dict()
    assert snapshot["plugin_configs"]["alpha"]["api_key"] == "<redacted>"
    assert (
        snapshot["plugin_configs"]["alpha"]["nested"]["access_token"]
        == "<redacted>"
    )


def test_unredacted_snapshot_is_deterministically_sorted(
    framework: Path,
    project: Path,
) -> None:
    config = ResolvedConfig(
        project_path=project,
        auditors=("all",),
        output_formats=("json",),
        config_path=None,
        fail_on=(),
        exclude=(),
        output_dir=framework / "out",
        plugins_dir=framework / "plugins",
        framework_root=framework,
        plugin_defaults={"zeta": 1, "alpha": 2},
        plugin_configs={"zeta": {"b": 1, "a": 2}},
    )
    snapshot = config.to_dict(redact_sensitive=False)
    assert list(snapshot["plugin_defaults"]) == ["alpha", "zeta"]
    assert list(snapshot["plugin_configs"]["zeta"]) == ["a", "b"]

# ---------------------------------------------------------------------
# SARIF output-format support — Fase 3.5
# ---------------------------------------------------------------------


def test_normalize_output_formats_accepts_sarif() -> None:
    assert normalize_output_formats("sarif") == ("sarif",)


def test_normalize_output_formats_combines_and_deduplicates_sarif() -> None:
    assert normalize_output_formats("markdown,SARIF,json,sarif") == (
        "markdown",
        "sarif",
        "json",
    )


def test_resolve_sarif_from_json(framework: Path, project: Path) -> None:
    config_path = framework / "sarif.json"
    config_path.write_text(
        json.dumps({"project_path": str(project), "output_formats": ["sarif"]}),
        encoding="utf-8",
    )
    config = resolve_global_config(
        config_path=config_path,
        framework_root_default=framework,
    )
    assert config.output_formats == ("sarif",)


def test_resolve_sarif_from_toml(framework: Path, project: Path) -> None:
    config_path = framework / "sarif.toml"
    config_path.write_text(
        f'project_path = {str(project)!r}\noutput_formats = ["sarif"]\n',
        encoding="utf-8",
    )
    config = resolve_global_config(
        config_path=config_path,
        framework_root_default=framework,
    )
    assert config.output_formats == ("sarif",)


def test_resolve_sarif_from_yaml(framework: Path, project: Path) -> None:
    config_path = framework / "sarif.yaml"
    config_path.write_text(
        f"project_path: {project}\noutput_formats: [sarif]\n",
        encoding="utf-8",
    )
    config = resolve_global_config(
        config_path=config_path,
        framework_root_default=framework,
    )
    assert config.output_formats == ("sarif",)


def test_sarif_is_opt_in_and_defaults_remain_historical(
    framework: Path,
    project: Path,
) -> None:
    config = resolve_global_config(
        cli_values={"project_path": str(project)},
        explicit_cli_fields={"project_path"},
        framework_root_default=framework,
    )
    assert config.output_formats == ("markdown", "json")
