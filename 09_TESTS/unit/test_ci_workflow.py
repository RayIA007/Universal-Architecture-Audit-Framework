"""Contract tests for the repository's GitHub Actions CI workflow."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "uaaf-ci.yml"


def _workflow_text() -> str:
    """Return the workflow as normalized UTF-8 text."""
    return WORKFLOW_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")


def _top_level_block(text: str, key: str) -> str:
    """Extract one top-level YAML block without implementing a YAML parser."""
    lines = text.splitlines()
    marker = f"{key}:"
    try:
        start = lines.index(marker)
    except ValueError as error:
        raise AssertionError(f"Missing top-level workflow block: {marker}") from error

    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line and not line[0].isspace() and re.match(
            r"^[A-Za-z0-9_-]+:\s*$",
            line,
        ):
            end = index
            break
    return "\n".join(lines[start:end])


def test_workflow_exists() -> None:
    assert WORKFLOW_PATH.is_file()


def test_workflow_is_nonempty_utf8_text() -> None:
    text = _workflow_text()
    assert text.strip()
    assert "\x00" not in text


def test_workflow_has_clear_name() -> None:
    assert re.search(r"(?m)^name:\s+UAAF CI\s*$", _workflow_text())


@pytest.mark.parametrize("event", ["push", "pull_request", "workflow_dispatch"])
def test_workflow_declares_required_events(event: str) -> None:
    event_block = _top_level_block(_workflow_text(), "on")
    assert re.search(rf"(?m)^  {re.escape(event)}:\s*$", event_block)


def test_push_and_pull_request_target_main() -> None:
    event_block = _top_level_block(_workflow_text(), "on")
    assert re.search(
        r"(?ms)^  push:\s*\n    branches:\s*\n      - main\s*$",
        event_block,
    )
    assert re.search(
        r"(?ms)^  pull_request:\s*\n    branches:\s*\n      - main\s*$",
        event_block,
    )


def test_workflow_avoids_privileged_or_unneeded_events() -> None:
    text = _workflow_text().casefold()
    assert "pull_request_target" not in text
    assert not re.search(r"(?m)^\s*schedule:\s*$", text)
    assert not re.search(r"(?m)^\s*workflow_run:\s*$", text)


def test_permissions_are_read_only() -> None:
    permissions = _top_level_block(_workflow_text(), "permissions")
    permission_lines = [
        line.strip()
        for line in permissions.splitlines()[1:]
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert permission_lines == ["contents: read"]


def test_workflow_has_one_canonical_quality_job() -> None:
    jobs = _top_level_block(_workflow_text(), "jobs")
    assert re.search(r"(?m)^  quality:\s*$", jobs)
    assert len(re.findall(r"(?m)^  [A-Za-z0-9_-]+:\s*$", jobs)) == 1


def test_workflow_uses_windows_runner_without_matrix() -> None:
    text = _workflow_text()
    assert re.search(r"(?m)^    runs-on:\s+windows-latest\s*$", text)
    assert not re.search(r"(?m)^\s*matrix:\s*$", text)


def test_workflow_has_bounded_execution_time() -> None:
    assert re.search(r"(?m)^    timeout-minutes:\s+15\s*$", _workflow_text())


def test_workflow_cancels_superseded_runs() -> None:
    concurrency = _top_level_block(_workflow_text(), "concurrency")
    assert "github.workflow" in concurrency
    assert "github.ref" in concurrency
    assert re.search(r"(?m)^  cancel-in-progress:\s+true\s*$", concurrency)


def test_checkout_is_official_and_does_not_persist_credentials() -> None:
    text = _workflow_text()
    assert "uses: actions/checkout@v7" in text
    assert re.search(r"(?m)^          fetch-depth:\s+1\s*$", text)
    assert re.search(
        r"(?m)^          persist-credentials:\s+false\s*$",
        text,
    )


def test_setup_python_is_official_and_pins_python() -> None:
    text = _workflow_text()
    assert "uses: actions/setup-python@v7" in text
    assert re.search(
        r"""(?m)^          python-version:\s+["']3\.14\.6["']\s*$""",
        text,
    )
    assert re.search(r"(?m)^          architecture:\s+x64\s*$", text)


def test_only_expected_official_actions_are_used() -> None:
    uses = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", _workflow_text())
    assert uses == ["actions/checkout@v7", "actions/setup-python@v7"]


@pytest.mark.parametrize("mutable_ref", ["@main", "@master", "@latest"])
def test_actions_do_not_use_mutable_branch_references(mutable_ref: str) -> None:
    assert mutable_ref not in _workflow_text().casefold()


def test_environment_validation_uses_python_module_invocation() -> None:
    text = _workflow_text()
    assert "python --version" in text
    assert "python -m pip --version" in text


def test_dependency_installation_is_minimal_and_pinned() -> None:
    text = _workflow_text()
    assert re.search(
        r"python -m pip install[^\n]*pytest==9\.1\.1",
        text,
    )
    assert "pip install -e" not in text.casefold()
    assert "requirements.txt" not in text.casefold()


def test_complete_pytest_suite_is_executed() -> None:
    text = _workflow_text()
    assert re.search(r"(?m)^\s*run:\s+python -m pytest -q\s*$", text)
    assert "713 passed" not in text


def test_cli_help_is_executed() -> None:
    assert re.search(
        r"(?m)^\s*run:\s+python run\.py --help\s*$",
        _workflow_text(),
    )


def test_smoke_test_uses_controlled_project_and_subset() -> None:
    text = _workflow_text()
    assert '--project-path "12_EXAMPLES/sample_project"' in text
    assert '--auditors "configuration"' in text
    assert '--output-formats "markdown,json"' in text


def test_smoke_test_uses_runner_temp_and_validates_exit_code() -> None:
    text = _workflow_text()
    assert "$env:RUNNER_TEMP" in text
    assert "--output-dir $smokeOutput" in text
    assert "$LASTEXITCODE -ne 0" in text
    assert "07_OUTPUTS" not in text


def test_smoke_test_validates_both_report_formats() -> None:
    text = _workflow_text()
    assert '-Filter "*.md"' in text
    assert '-Filter "*.json"' in text
    assert "Markdown report" in text
    assert "JSON report" in text


def test_workflow_does_not_upload_artifacts_or_enable_cache() -> None:
    text = _workflow_text().casefold()
    assert "upload-artifact" not in text
    assert not re.search(r"(?m)^\s*cache:\s*", text)


@pytest.mark.parametrize(
    "forbidden",
    [
        "git push",
        "git commit",
        "write-all",
        "contents: write",
        "curl ",
        "wget ",
        "invoke-webrequest",
        "start-process powershell",
        "remove-item -literalpath .",
    ],
)
def test_workflow_avoids_dangerous_or_write_operations(forbidden: str) -> None:
    assert forbidden not in _workflow_text().casefold()


def test_workflow_contains_no_secret_references_or_personal_paths() -> None:
    text = _workflow_text()
    assert "secrets." not in text.casefold()
    assert not re.search(r"(?i)\b[A-Z]:[\\/]", text)
    assert not re.search(r"(?i)users[\\/]", text)
