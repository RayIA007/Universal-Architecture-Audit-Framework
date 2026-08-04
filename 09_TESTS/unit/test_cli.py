"""Deterministic tests for UAAF CLI argument parsing and dispatch."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "08_SCRIPTS"
for import_root in (PROJECT_ROOT, SCRIPTS_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from uaaf_core import cli  # noqa: E402


def _success_result(*, exit_code: int = 0, report_paths: list[Path] | None = None):
    return SimpleNamespace(
        audit_results=[],
        consolidated_result={
            "metrics": {
                "auditor_count": 2,
                "findings_count": 3,
            }
        },
        report_paths=report_paths or [Path("07_OUTPUTS/report.md")],
        runtime_context=None,
        exit_code=exit_code,
    )


class _FakeOrchestrator:
    init_calls: list[dict[str, Any]] = []
    run_calls: list[dict[str, Any]] = []
    result = _success_result()
    error: Exception | None = None

    def __init__(self, **kwargs: Any) -> None:
        type(self).init_calls.append(dict(kwargs))

    def run(self, **kwargs: Any):
        type(self).run_calls.append(dict(kwargs))
        if type(self).error is not None:
            raise type(self).error
        return type(self).result


@pytest.fixture(autouse=True)
def _reset_fake() -> None:
    _FakeOrchestrator.init_calls = []
    _FakeOrchestrator.run_calls = []
    _FakeOrchestrator.result = _success_result()
    _FakeOrchestrator.error = None


def test_create_parser_uses_expected_program_name() -> None:
    assert cli.create_parser().prog == "python run.py"


def test_parse_args_defaults() -> None:
    args = cli.parse_args([])
    assert args.project_path == "."
    assert args.auditors == "all"
    assert args.output_formats == ("markdown", "json")
    assert args.config is None
    assert args.fail_on == ()
    assert args.exclude == []


def test_parse_args_project_path() -> None:
    args = cli.parse_args(["--project-path", "sample"])
    assert args.project_path == "sample"


def test_parse_args_auditor_subset_is_preserved() -> None:
    args = cli.parse_args(["--auditors", "architecture,testing"])
    assert args.auditors == "architecture,testing"


def test_parse_args_normalizes_output_formats() -> None:
    args = cli.parse_args(["--output-formats", "md,json"])
    assert args.output_formats == ("markdown", "json")


def test_parse_args_normalizes_fail_on() -> None:
    args = cli.parse_args(["--fail-on", "critical,error"])
    assert args.fail_on == ("critical", "error")


def test_parse_args_merges_repeated_excludes() -> None:
    args = cli.parse_args(
        ["--exclude", "generated,cache", "--exclude", "build"]
    )
    assert args.exclude == ["generated", "cache", "build"]


def test_parse_args_preserves_exclude_case() -> None:
    args = cli.parse_args(["--exclude", "Generated"])
    assert args.exclude == ["Generated"]


def test_parse_args_config_path() -> None:
    args = cli.parse_args(["--config", "uaaf.yaml"])
    assert args.config == "uaaf.yaml"


def test_parse_args_output_dir() -> None:
    args = cli.parse_args(["--output-dir", "reports"])
    assert args.output_dir == "reports"


def test_parse_args_plugins_dir() -> None:
    args = cli.parse_args(["--plugins-dir", "custom_plugins"])
    assert args.plugins_dir == "custom_plugins"


def test_parse_args_framework_root() -> None:
    args = cli.parse_args(["--framework-root", "framework"])
    assert args.framework_root == "framework"


def test_parse_args_rejects_invalid_output_format() -> None:
    with pytest.raises(SystemExit) as error:
        cli.parse_args(["--output-formats", "xml"])
    assert error.value.code == 2


def test_parse_args_rejects_invalid_fail_on() -> None:
    with pytest.raises(SystemExit) as error:
        cli.parse_args(["--fail-on", "fatal"])
    assert error.value.code == 2


def test_parse_args_rejects_exclude_path() -> None:
    with pytest.raises(SystemExit) as error:
        cli.parse_args(["--exclude", "generated/cache"])
    assert error.value.code == 2


def test_parse_args_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        cli.parse_args(["--help"])
    assert error.value.code == 0
    assert "--project-path" in capsys.readouterr().out


def test_main_constructs_orchestrator_with_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "UnifiedOrchestrator", _FakeOrchestrator)
    code = cli.main(
        [
            "--framework-root",
            "framework",
            "--plugins-dir",
            "plugins",
        ]
    )
    assert code == 0
    assert _FakeOrchestrator.init_calls == [
        {"framework_root": "framework", "plugins_dir": "plugins"}
    ]


def test_main_passes_normalized_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "UnifiedOrchestrator", _FakeOrchestrator)
    code = cli.main(
        [
            "--project-path",
            "target",
            "--auditors",
            "architecture,testing",
            "--output-formats",
            "json",
            "--config",
            "uaaf.yaml",
            "--fail-on",
            "critical,error",
            "--exclude",
            "generated,cache",
            "--output-dir",
            "reports",
        ]
    )
    assert code == 0
    call = _FakeOrchestrator.run_calls[0]
    assert call["project_path"] == Path("target")
    assert call["auditors"] == "architecture,testing"
    assert call["output_formats"] == ("json",)
    assert call["config_path"] == "uaaf.yaml"
    assert call["fail_on"] == ("critical", "error")
    assert call["exclude"] == ["generated", "cache"]
    assert call["output_dir"] == "reports"


def test_main_returns_orchestrator_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "UnifiedOrchestrator", _FakeOrchestrator)
    _FakeOrchestrator.result = _success_result(exit_code=1)
    assert cli.main([]) == 1


def test_main_prints_summary(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli, "UnifiedOrchestrator", _FakeOrchestrator)
    cli.main([])
    output = capsys.readouterr().out
    assert "2 auditor(s)" in output
    assert "3 finding(s)" in output


def test_main_prints_every_report_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "UnifiedOrchestrator", _FakeOrchestrator)
    _FakeOrchestrator.result = _success_result(
        report_paths=[Path("one.md"), Path("two.json")]
    )
    cli.main([])
    output = capsys.readouterr().out
    assert "Report: one.md" in output
    assert "Report: two.json" in output


def test_main_returns_two_for_value_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "UnifiedOrchestrator", _FakeOrchestrator)
    _FakeOrchestrator.error = ValueError("bad configuration")
    assert cli.main([]) == 2
    assert "UAAF error: bad configuration" in capsys.readouterr().err


def test_main_returns_two_for_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "UnifiedOrchestrator", _FakeOrchestrator)
    _FakeOrchestrator.error = RuntimeError("runtime failed")
    assert cli.main([]) == 2
    assert "runtime failed" in capsys.readouterr().err


def test_main_returns_two_for_os_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "UnifiedOrchestrator", _FakeOrchestrator)
    _FakeOrchestrator.error = OSError("filesystem failed")
    assert cli.main([]) == 2
    assert "filesystem failed" in capsys.readouterr().err


def test_main_does_not_write_error_on_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "UnifiedOrchestrator", _FakeOrchestrator)
    assert cli.main([]) == 0
    assert capsys.readouterr().err == ""