"""
Test Suite J: Configuration Auditor — 56 deterministas tests
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# Bootstrap paths (mismo patrón que usan los otros test suites)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _PROJECT_ROOT / "08_SCRIPTS"
_PLUGINS_DIR = _PROJECT_ROOT / "plugins"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_PLUGINS_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGINS_DIR))

import pytest

from uaaf_core.audit.audit_result import (
    AuditStatus,
    FindingSeverity,
    validate_audit_result,
)
from plugins.configuration.configuration_auditor import (
    PLUGIN_ID,
    PLUGIN_VERSION,
    AUDIT_TYPE,
    ConfigurationAuditorPlugin,
    run,
    _discover_config_files,
    _try_parse_config,
    _check_invalid_syntax,
    _check_secrets,
    _check_duplicates,
    _check_missing_required,
    _extract_key_value_pairs,
    _flatten_dict,
    _validate_context,
    _validate_ignored_directories,
    _validate_string_set,
    _validate_string_list,
    _extract_key_from_line,
)

# =====================================================================
# FIXTURES
# =====================================================================


@pytest.fixture
def temp_project():
    """Yield a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def plugin():
    return ConfigurationAuditorPlugin()


def _write_file(project_path: Path, relative_path: str, content: str) -> None:
    """Helper to write a file in the temp project."""
    file_path = project_path / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


# =====================================================================
# TESTS: Context Validation (1-8)
# =====================================================================


class TestContextValidation:
    def test_context_must_be_dict(self, plugin, temp_project):
        with pytest.raises(TypeError, match="context must be a dictionary"):
            plugin.execute("not a dict")

    def test_context_missing_project_path(self, plugin):
        with pytest.raises(ValueError, match="project_path"):
            plugin.execute({})

    def test_context_invalid_project_path(self, plugin):
        with pytest.raises(ValueError, match="project_path"):
            plugin.execute({"project_path": "/nonexistent/path/12345"})

    def test_context_unknown_fields(self, plugin, temp_project):
        with pytest.raises(ValueError, match="unknown fields"):
            plugin.execute({"project_path": str(temp_project), "foo": "bar"})

    def test_context_audit_type_mismatch(self, plugin, temp_project):
        with pytest.raises(ValueError, match="audit_type"):
            plugin.execute(
                {"project_path": str(temp_project), "audit_type": "architecture"}
            )

    def test_validate_ignored_directories_rejects_path(self):
        with pytest.raises(ValueError, match="directory names"):
            _validate_ignored_directories(["some/path"])

    def test_validate_string_set_rejects_empty(self):
        with pytest.raises(ValueError, match="non-empty strings"):
            _validate_string_set(["a", ""], "field")

    def test_validate_string_list_rejects_empty(self):
        with pytest.raises(ValueError, match="non-empty strings"):
            _validate_string_list(["a", ""], "field")


# =====================================================================
# TESTS: Discovery (9-14)
# =====================================================================


class TestDiscovery:
    def test_discover_json_file(self, temp_project):
        (temp_project / "settings.json").write_text('{"a": 1}')
        files = _discover_config_files(
            temp_project, frozenset(), frozenset([".json"])
        )
        assert files == ["settings.json"]

    def test_discover_yaml_file(self, temp_project):
        (temp_project / "config.yaml").write_text("key: value")
        files = _discover_config_files(
            temp_project, frozenset(), frozenset([".yaml", ".yml"])
        )
        assert files == ["config.yaml"]

    def test_discover_env_file(self, temp_project):
        (temp_project / ".env").write_text("KEY=val")
        files = _discover_config_files(
            temp_project, frozenset(), frozenset([".env"])
        )
        assert files == [".env"]

    def test_discover_ignores_directories(self, temp_project):
        (temp_project / ".venv").mkdir()
        (temp_project / ".venv" / "settings.json").write_text('{"a": 1}')
        files = _discover_config_files(
            temp_project,
            frozenset([".venv"]),
            frozenset([".json"]),
        )
        assert files == []

    def test_discover_multiple_extensions(self, temp_project):
        (temp_project / "a.json").write_text("{}")
        (temp_project / "b.yaml").write_text("k: v")
        (temp_project / "c.toml").write_text("[section]")
        files = _discover_config_files(
            temp_project,
            frozenset(),
            frozenset([".json", ".yaml", ".toml"]),
        )
        assert files == ["a.json", "b.yaml", "c.toml"]

    def test_discover_sorted_order(self, temp_project):
        (temp_project / "z.yaml").write_text("k: v")
        (temp_project / "a.json").write_text("{}")
        files = _discover_config_files(
            temp_project, frozenset(), frozenset([".json", ".yaml"])
        )
        assert files == ["a.json", "z.yaml"]


# =====================================================================
# TESTS: Syntax Validation (15-22)
# =====================================================================


class TestSyntaxValidation:
    def test_try_parse_valid_json(self, temp_project):
        assert _try_parse_config(temp_project / "a.json", '{"x": 1}', ".json", "a.json") is None

    def test_try_parse_invalid_json(self, temp_project):
        err = _try_parse_config(temp_project / "a.json", "{bad", ".json", "a.json")
        assert err is not None
        assert "Expecting" in err or "JSON" in err

    def test_try_parse_valid_ini(self, temp_project):
        text = "[section]\nkey = value\n"
        assert _try_parse_config(temp_project / "a.ini", text, ".ini", "a.ini") is None

    def test_try_parse_invalid_ini(self, temp_project):
        text = "[section\nkey = value\n"
        err = _try_parse_config(temp_project / "a.ini", text, ".ini", "a.ini")
        assert err is not None

    def test_try_parse_valid_env(self, temp_project):
        assert _try_parse_config(temp_project / ".env", "KEY=val\n", ".env", ".env") is None

    def test_try_parse_invalid_env(self, temp_project):
        err = _try_parse_config(temp_project / ".env", "NOEQUALSIGN\n", ".env", ".env")
        assert err is not None

    def test_check_invalid_syntax_finds_errors(self, temp_project):
        (temp_project / "bad.json").write_text("{invalid")
        files = ["bad.json"]
        violations = _check_invalid_syntax(files, temp_project)
        assert len(violations) == 1
        assert violations[0]["type"] == "invalid_syntax"

    def test_check_invalid_syntax_passes_valid(self, temp_project):
        (temp_project / "good.json").write_text('{"ok": true}')
        files = ["good.json"]
        violations = _check_invalid_syntax(files, temp_project)
        assert len(violations) == 0


# =====================================================================
# TESTS: Secret Detection (23-28)
# =====================================================================


class TestSecretDetection:
    def test_check_secrets_api_key(self, temp_project):
        (temp_project / "secrets.env").write_text("API_KEY=sk-1234567890abcdef1234\n")
        files = ["secrets.env"]
        from plugins.configuration.configuration_auditor import _DEFAULT_SECRET_PATTERNS
        violations = _check_secrets(files, temp_project, _DEFAULT_SECRET_PATTERNS)
        assert len(violations) >= 1
        assert any("API_KEY" in v["message"] for v in violations)

    def test_check_secrets_password(self, temp_project):
        (temp_project / "config.ini").write_text("password = supersecret123\n")
        files = ["config.ini"]
        from plugins.configuration.configuration_auditor import _DEFAULT_SECRET_PATTERNS
        violations = _check_secrets(files, temp_project, _DEFAULT_SECRET_PATTERNS)
        assert len(violations) >= 1

    def test_check_secrets_sk_prefix(self, temp_project):
        (temp_project / "keys.json").write_text('{"openai": "sk-abcdefghijklmnopqrstuvwxyz1234"}')
        files = ["keys.json"]
        from plugins.configuration.configuration_auditor import _DEFAULT_SECRET_PATTERNS
        violations = _check_secrets(files, temp_project, _DEFAULT_SECRET_PATTERNS)
        assert len(violations) >= 1
        # Raw violations have matched_pattern at top level, not nested in details
        assert any("sk-" in v["matched_pattern"] for v in violations)

    def test_check_secrets_aknia(self, temp_project):
        (temp_project / "aws.env").write_text("AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n")
        files = ["aws.env"]
        from plugins.configuration.configuration_auditor import _DEFAULT_SECRET_PATTERNS
        violations = _check_secrets(files, temp_project, _DEFAULT_SECRET_PATTERNS)
        assert len(violations) >= 1

    def test_check_secrets_no_false_positives(self, temp_project):
        (temp_project / "safe.yaml").write_text("debug: false\n")
        files = ["safe.yaml"]
        from plugins.configuration.configuration_auditor import _DEFAULT_SECRET_PATTERNS
        violations = _check_secrets(files, temp_project, _DEFAULT_SECRET_PATTERNS)
        assert len(violations) == 0

    def test_extract_key_from_line(self):
        import re
        line = "api_key = 'secret123'"
        match = re.search(r"(?i)api[_-]?key\s*[=:]\s*['\"]?([^\s'\"]+)['\"]?", line)
        assert match is not None
        key = _extract_key_from_line(line, match)
        assert key == "api_key"


# =====================================================================
# TESTS: Duplicate Detection (29-34)
# =====================================================================


class TestDuplicateDetection:
    def test_check_duplicates_finds_same_value(self, temp_project):
        (temp_project / "a.json").write_text('{"key": "value"}')
        (temp_project / "b.json").write_text('{"key": "value"}')
        files = ["a.json", "b.json"]
        violations = _check_duplicates(
            files, temp_project, frozenset([".json"])
        )
        assert len(violations) == 2
        assert all(v["key"] == "key" for v in violations)

    def test_check_duplicates_no_false_positive(self, temp_project):
        (temp_project / "a.json").write_text('{"key": "value1"}')
        (temp_project / "b.json").write_text('{"key": "value2"}')
        files = ["a.json", "b.json"]
        violations = _check_duplicates(
            files, temp_project, frozenset([".json"])
        )
        assert len(violations) == 0

    def test_extract_key_value_pairs_json(self, temp_project):
        pairs = _extract_key_value_pairs(
            temp_project / "a.json", '{"x": 1, "y": {"z": 2}}', frozenset([".json"])
        )
        assert ("x", "1") in pairs
        assert ("y.z", "2") in pairs

    def test_extract_key_value_pairs_env(self, temp_project):
        pairs = _extract_key_value_pairs(
            temp_project / ".env", "FOO=bar\nBAZ=qux\n", frozenset([".env"])
        )
        assert ("FOO", "bar") in pairs
        assert ("BAZ", "qux") in pairs

    def test_flatten_dict_nested(self):
        data = {"a": {"b": {"c": 1}}, "d": "two"}
        flat = _flatten_dict(data)
        assert ("a.b.c", "1") in flat
        assert ("d", "two") in flat

    def test_flatten_dict_non_dict_returns_empty(self):
        assert _flatten_dict("string") == []
        assert _flatten_dict(123) == []


# =====================================================================
# TESTS: Missing Required Files (35-38)
# =====================================================================


class TestMissingRequired:
    def test_check_missing_required_finds_missing(self, temp_project):
        required = frozenset(["pyproject.toml", ".env"])
        violations = _check_missing_required(temp_project, required)
        assert len(violations) == 2
        assert all(v["type"] == "missing_required_config" for v in violations)

    def test_check_missing_required_finds_none_when_present(self, temp_project):
        (temp_project / "pyproject.toml").write_text("[build-system]\n")
        required = frozenset(["pyproject.toml"])
        violations = _check_missing_required(temp_project, required)
        assert len(violations) == 0

    def test_check_missing_required_empty_set(self, temp_project):
        violations = _check_missing_required(temp_project, frozenset())
        assert len(violations) == 0

    def test_check_missing_required_sorted_order(self, temp_project):
        required = frozenset(["z.cfg", "a.ini"])
        violations = _check_missing_required(temp_project, required)
        files = [v["required_file"] for v in violations]
        assert files == ["a.ini", "z.cfg"]


# =====================================================================
# TESTS: End-to-End / Integration (39-45)
# =====================================================================


class TestEndToEnd:
    def test_run_empty_project_completes(self, temp_project):
        # Override defaults so no required-file findings are emitted
        result = run(
            {
                "project_path": str(temp_project),
                "required_config_files": [],
            }
        )
        assert result["plugin_id"] == PLUGIN_ID
        assert result["plugin_version"] == PLUGIN_VERSION
        assert result["audit_type"] == AUDIT_TYPE
        assert result["status"] == AuditStatus.COMPLETED.value
        assert result["metrics"]["config_file_count"] == 0
        validate_audit_result(result)

    def test_run_finds_missing_required(self, temp_project):
        result = run(
            {
                "project_path": str(temp_project),
                "required_config_files": ["missing.toml"],
            }
        )
        assert result["status"] == AuditStatus.COMPLETED_WITH_FINDINGS.value
        findings = result["findings"]
        assert any(f["code"] == "CONFIG-MISSING-001" for f in findings)
        validate_audit_result(result)

    def test_run_finds_invalid_json(self, temp_project):
        (temp_project / "bad.json").write_text("{invalid")
        result = run({"project_path": str(temp_project)})
        assert result["status"] == AuditStatus.COMPLETED_WITH_FINDINGS.value
        findings = result["findings"]
        assert any(f["code"] == "CONFIG-INVALID-001" for f in findings)
        validate_audit_result(result)

    def test_run_finds_secret(self, temp_project):
        (temp_project / "keys.env").write_text("API_KEY=sk-1234567890abcdef1234\n")
        result = run({"project_path": str(temp_project)})
        assert result["status"] == AuditStatus.COMPLETED_WITH_FINDINGS.value
        findings = result["findings"]
        assert any(f["code"] == "CONFIG-SECRET-001" for f in findings)
        assert any(f["severity"] == FindingSeverity.CRITICAL.value for f in findings)
        validate_audit_result(result)

    def test_run_finds_duplicates(self, temp_project):
        (temp_project / "a.json").write_text('{"db": "postgres"}')
        (temp_project / "b.yaml").write_text("db: postgres")
        result = run({"project_path": str(temp_project)})
        assert result["status"] == AuditStatus.COMPLETED_WITH_FINDINGS.value
        findings = result["findings"]
        assert any(f["code"] == "CONFIG-DUPLICATE-001" for f in findings)
        validate_audit_result(result)

    def test_run_ignores_directories(self, temp_project):
        (temp_project / "node_modules").mkdir()
        (temp_project / "node_modules" / "package.json").write_text("{}")
        result = run({"project_path": str(temp_project)})
        assert result["metrics"]["config_file_count"] == 0
        validate_audit_result(result)

    def test_run_with_custom_extensions(self, temp_project):
        (temp_project / "custom.conf").write_text("key=val")
        result = run(
            {
                "project_path": str(temp_project),
                "config_extensions": [".conf"],
            }
        )
        assert result["metrics"]["config_file_count"] == 1
        validate_audit_result(result)


# =====================================================================
# TESTS: Plugin Wrapper (46-48)
# =====================================================================


class TestPluginWrapper:
    def test_plugin_wrapper_execute_returns_dict(self, plugin, temp_project):
        result = plugin.execute({"project_path": str(temp_project)})
        assert isinstance(result, dict)
        validate_audit_result(result)

    def test_plugin_wrapper_id_matches(self):
        p = ConfigurationAuditorPlugin()
        result = p.execute({"project_path": str(Path(__file__).parent)})
        assert result["plugin_id"] == PLUGIN_ID

    def test_plugin_wrapper_version_matches(self):
        p = ConfigurationAuditorPlugin()
        result = p.execute({"project_path": str(Path(__file__).parent)})
        assert result["plugin_version"] == PLUGIN_VERSION


# =====================================================================
# TESTS: Edge Cases & Robustness (49-52)
# =====================================================================


class TestEdgeCases:
    def test_run_with_binary_file_ignored(self, temp_project):
        (temp_project / "binary.json").write_bytes(b"\x00\x01\x02")
        result = run({"project_path": str(temp_project)})
        validate_audit_result(result)

    def test_run_with_empty_config_file(self, temp_project):
        (temp_project / "empty.yaml").write_text("")
        result = run({"project_path": str(temp_project)})
        validate_audit_result(result)

    def test_run_with_comment_only_env(self, temp_project):
        (temp_project / ".env").write_text("# This is a comment\n")
        result = run({"project_path": str(temp_project)})
        validate_audit_result(result)

    def test_run_multiple_findings_types(self, temp_project):
        (temp_project / "bad.json").write_text("{invalid")
        (temp_project / "keys.env").write_text("SECRET=shhh\n")
        (temp_project / "a.json").write_text('{"dup": "val"}')
        (temp_project / "b.json").write_text('{"dup": "val"}')
        result = run({"project_path": str(temp_project)})
        codes = {f["code"] for f in result["findings"]}
        assert "CONFIG-INVALID-001" in codes
        assert "CONFIG-SECRET-001" in codes
        assert "CONFIG-DUPLICATE-001" in codes
        validate_audit_result(result)


# =====================================================================
# TESTS: Metrics & Summary (53-56)
# =====================================================================


class TestMetricsAndSummary:
    def test_metrics_counts_are_integers(self, temp_project):
        (temp_project / "a.json").write_text("{}")
        result = run({"project_path": str(temp_project)})
        metrics = result["metrics"]
        assert isinstance(metrics["config_file_count"], int)
        assert isinstance(metrics["findings_count"], int)

    def test_summary_contains_project_path(self, temp_project):
        result = run({"project_path": str(temp_project)})
        # Use resolved paths for comparison (Windows 8.3 vs long name)
        assert Path(result["summary"]["project_path"]).resolve() == temp_project.resolve()

    def test_execution_timestamps_present(self, temp_project):
        result = run({"project_path": str(temp_project)})
        assert result["execution"]["started_at"] is not None
        assert result["execution"]["completed_at"] is not None

    def test_findings_list_is_list(self, temp_project):
        result = run({"project_path": str(temp_project)})
        assert isinstance(result["findings"], list)