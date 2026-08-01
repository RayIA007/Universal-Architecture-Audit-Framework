"""
Test Suite F - Architecture Auditor Runtime Pipeline integration.

Run from the UAAF project root:

    python -m pytest -q 09_TESTS/integration/test_architecture_pipeline.py

The Runtime Pipeline registers ProcessorContract implementations. The
Architecture Auditor keeps its functional run(context) contract, so this suite
uses a test-local processor adapter with the same plugin identifier.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "08_SCRIPTS"

for import_root in (PROJECT_ROOT, SCRIPTS_ROOT):
    import_root_text = str(import_root)

    if import_root_text not in sys.path:
        sys.path.insert(0, import_root_text)


from plugins.architecture import architecture_auditor  # noqa: E402
from uaaf_core.audit.audit_result import (  # noqa: E402
    AuditExecution,
    AuditFinding,
    AuditResult,
    AuditStatus,
    FindingSeverity,
    validate_audit_result,
)
from uaaf_core.contracts.processor import ProcessorContract  # noqa: E402
from uaaf_core.kernel import UAAFKernel  # noqa: E402
from uaaf_core.models.enums import (  # noqa: E402
    AuditDomain,
    ComplianceLevel,
    SessionStatus,
)
from uaaf_core.models.profile import AuditProfile  # noqa: E402
from uaaf_core.registry import UAAFRegistry  # noqa: E402
from uaaf_core.runtime.runtime_context import RuntimeContext  # noqa: E402


ARCHITECTURE_PLUGIN_ID = getattr(
    architecture_auditor,
    "PLUGIN_ID",
    "architecture-auditor",
)

ARCHITECTURE_PLUGIN_VERSION = getattr(
    architecture_auditor,
    "PLUGIN_VERSION",
    "1.0.0",
)

PROFILE_ID = "architecture-pipeline-integration"

PLUGIN_OPTIONS_CONTEXT_KEY = "architecture_auditor_options"
PLUGIN_INPUT_CONTEXT_KEY = "architecture_auditor_input"
PLUGIN_RESULT_CONTEXT_KEY = "architecture_auditor_result"
PLUGIN_RESULT_OUTPUT_KEY = "audit_result"

FIXED_STARTED_AT = "2026-08-01T12:00:00+00:00"
FIXED_COMPLETED_AT = "2026-08-01T12:00:00.025000+00:00"
FIXED_DURATION_MS = 25


class ArchitecturePluginExecutionError(RuntimeError):
    """Raised when the Architecture Auditor reports a failed execution."""


class ArchitectureAuditorPipelineProcessor(ProcessorContract):
    """
    Runtime Pipeline adapter for the functional Architecture Auditor.

    The adapter:

    1. Receives the active AuditSession from Runtime Pipeline.
    2. Builds the Architecture Auditor context dictionary.
    3. Executes architecture_auditor.run().
    4. Validates the returned canonical AuditResult.
    5. Preserves that result in both session context and processor output.
    """

    processor_id = ARCHITECTURE_PLUGIN_ID
    processor_version = ARCHITECTURE_PLUGIN_VERSION
    processor_description = (
        "Architecture Auditor adapter for Runtime Pipeline integration."
    )

    def validate(self, session: Any) -> None:
        if session.status is not SessionStatus.RUNNING:
            raise RuntimeError(
                "Architecture Auditor requires a running AuditSession."
            )

        options = session.get_context(
            PLUGIN_OPTIONS_CONTEXT_KEY,
            {},
        )

        if not isinstance(options, dict):
            raise TypeError(
                f"{PLUGIN_OPTIONS_CONTEXT_KEY!r} must be a dictionary."
            )

    def execute(self, session: Any) -> None:
        options = dict(
            session.get_context(
                PLUGIN_OPTIONS_CONTEXT_KEY,
                {},
            )
        )

        plugin_context: dict[str, Any] = {
            "project_path": str(session.audit.target_path),
            "audit_type": "architecture",
        }
        plugin_context.update(options)

        session.set_context(
            PLUGIN_INPUT_CONTEXT_KEY,
            dict(plugin_context),
        )

        audit_result = architecture_auditor.run(plugin_context)

        validate_audit_result(audit_result)

        session.set_context(
            PLUGIN_RESULT_CONTEXT_KEY,
            audit_result,
        )

        self.add_output(
            PLUGIN_RESULT_OUTPUT_KEY,
            audit_result,
        )

        status = audit_result["status"]

        if status == AuditStatus.COMPLETED_WITH_FINDINGS.value:
            self.add_warning(
                "Architecture Auditor completed with findings."
            )
            return

        if status in {
            AuditStatus.COMPLETED_WITH_ERRORS.value,
            AuditStatus.FAILED.value,
        }:
            raise ArchitecturePluginExecutionError(
                "Architecture Auditor returned terminal status "
                f"{status!r}."
            )


def _architecture_metrics(
    *,
    findings_count: int = 0,
    python_file_count: int = 1,
    module_count: int = 1,
    package_count: int = 0,
) -> dict[str, int]:
    return {
        "python_file_count": python_file_count,
        "module_count": module_count,
        "package_count": package_count,
        "local_import_count": 0,
        "dependency_edge_count": 0,
        "circular_dependency_count": 0,
        "forbidden_import_count": 0,
        "layer_violation_count": 0,
        "missing_package_initializer_count": 0,
        "findings_count": findings_count,
    }


def _canonical_result(
    *,
    status: AuditStatus,
    project_path: Path,
    findings: tuple[AuditFinding, ...] = (),
    errors: tuple[str, ...] = (),
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_metrics = (
        dict(metrics)
        if metrics is not None
        else _architecture_metrics(
            findings_count=len(findings),
        )
    )

    normalized_metrics["findings_count"] = len(findings)

    return AuditResult(
        plugin_id=ARCHITECTURE_PLUGIN_ID,
        plugin_version=ARCHITECTURE_PLUGIN_VERSION,
        audit_type="architecture",
        status=status,
        summary={
            "project_path": str(project_path.resolve()),
            "python_files": ["main.py"],
            "modules": ["main"],
            "packages": [],
            "dependency_cycles": [],
        },
        metrics=normalized_metrics,
        findings=findings,
        errors=errors,
        execution=AuditExecution(
            started_at=FIXED_STARTED_AT,
            completed_at=FIXED_COMPLETED_AT,
            duration_ms=FIXED_DURATION_MS,
        ),
    ).to_dict()


def _warning_finding() -> AuditFinding:
    return AuditFinding(
        code="ARCH_MISSING_PACKAGE_INITIALIZER",
        severity=FindingSeverity.WARNING,
        path="sample_package",
        message=(
            "Package directory does not contain __init__.py."
        ),
        details={
            "package": "sample_package",
            "expected_path": (
                "sample_package/__init__.py"
            ),
        },
    )


def _create_python_project(root: Path) -> Path:
    project_path = root / "project"
    package_path = project_path / "sample_package"

    package_path.mkdir(parents=True)

    (package_path / "__init__.py").write_text(
        '"""Integration fixture package."""\n',
        encoding="utf-8",
    )

    (package_path / "module.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )

    (project_path / "main.py").write_text(
        "from sample_package.module import VALUE\n",
        encoding="utf-8",
    )

    return project_path


def _build_registry() -> UAAFRegistry:
    registry = UAAFRegistry()

    registry.register_processor(
        ArchitectureAuditorPipelineProcessor
    )

    profile = AuditProfile(
        profile_id=PROFILE_ID,
        name="Architecture Pipeline Integration",
        version="1.0.0",
        compliance_level=ComplianceLevel.CORE,
        domains=(
            AuditDomain.ARCHITECTURE,
        ),
        processor_ids=(
            ARCHITECTURE_PLUGIN_ID,
        ),
    )

    registry.register_profile(profile)

    return registry


def _create_runtime(
    *,
    tmp_path: Path,
    project_path: Path,
    plugin_options: dict[str, Any] | None = None,
) -> tuple[Any, UAAFRegistry]:
    registry = _build_registry()
    kernel = UAAFKernel(registry=registry)

    runtime = kernel.create_runtime(
        target_path=project_path,
        profile_id=PROFILE_ID,
        output_path=tmp_path / "outputs",
        workspace_path=tmp_path / "workspace",
        audit_metadata={
            "requested_by": "test-suite-f",
        },
        session_context={
            PLUGIN_OPTIONS_CONTEXT_KEY: dict(
                plugin_options or {}
            ),
        },
        runtime_metadata={
            "test_suite": "F",
            "integration_target": ARCHITECTURE_PLUGIN_ID,
        },
    )

    return runtime, registry


def _extract_audit_result(
    processor_result: Any,
) -> dict[str, Any]:
    for attribute_name in (
        "outputs",
        "output",
        "data",
    ):
        candidate = getattr(
            processor_result,
            attribute_name,
            None,
        )

        if (
            isinstance(candidate, Mapping)
            and PLUGIN_RESULT_OUTPUT_KEY in candidate
        ):
            value = candidate[PLUGIN_RESULT_OUTPUT_KEY]

            if isinstance(value, dict):
                return value

    for method_name in (
        "to_dict",
        "snapshot",
    ):
        method = getattr(
            processor_result,
            method_name,
            None,
        )

        if not callable(method):
            continue

        payload = method()

        if not isinstance(payload, Mapping):
            continue

        for container_name in (
            "outputs",
            "output",
            "data",
        ):
            candidate = payload.get(container_name)

            if (
                isinstance(candidate, Mapping)
                and PLUGIN_RESULT_OUTPUT_KEY in candidate
            ):
                value = candidate[
                    PLUGIN_RESULT_OUTPUT_KEY
                ]

                if isinstance(value, dict):
                    return value

    raise AssertionError(
        "ProcessorResult did not preserve the canonical "
        "Architecture Auditor result."
    )


def _runner_for(
    result_factory: Callable[
        [dict[str, Any]],
        dict[str, Any],
    ],
) -> Callable[
    [dict[str, Any]],
    dict[str, Any],
]:
    def runner(
        context: dict[str, Any],
    ) -> dict[str, Any]:
        result = result_factory(context)

        validate_audit_result(result)

        return result

    return runner


def test_architecture_plugin_registers_in_uaaf_registry() -> None:
    registry = _build_registry()

    assert registry.has_processor(
        ARCHITECTURE_PLUGIN_ID
    )

    processor = registry.create_processor(
        ARCHITECTURE_PLUGIN_ID
    )

    assert isinstance(
        processor,
        ArchitectureAuditorPipelineProcessor,
    )

    assert (
        processor.processor_id
        == ARCHITECTURE_PLUGIN_ID
    )


def test_kernel_executes_real_architecture_plugin_via_runtime_pipeline(
    tmp_path: Path,
) -> None:
    project_path = _create_python_project(tmp_path)

    runtime, registry = _create_runtime(
        tmp_path=tmp_path,
        project_path=project_path,
    )

    assert isinstance(
        runtime.context,
        RuntimeContext,
    )

    assert runtime.context.registry is registry
    assert runtime.context.profile_id == PROFILE_ID

    processor_results = runtime.run()

    assert len(processor_results) == 1
    assert runtime.is_terminal

    assert (
        runtime.context.get_metadata("pipeline_status")
        == "completed"
    )

    assert (
        runtime.context.get_metric(
            "processors_expected"
        )
        == 1
    )

    assert (
        runtime.context.get_metric(
            "processors_executed"
        )
        == 1
    )

    assert (
        runtime.context.get_metric(
            "processors_succeeded"
        )
        == 1
    )

    assert (
        runtime.context.get_metric(
            "processors_failed"
        )
        == 0
    )

    audit_result = _extract_audit_result(
        processor_results[0]
    )

    validate_audit_result(audit_result)

    assert (
        audit_result
        == runtime.context.session.get_context(
            PLUGIN_RESULT_CONTEXT_KEY
        )
    )

    assert (
        audit_result["plugin_id"]
        == ARCHITECTURE_PLUGIN_ID
    )

    assert audit_result["audit_type"] == "architecture"

    assert (
        audit_result["status"]
        == AuditStatus.COMPLETED.value
    )

    assert (
        audit_result["metrics"]["python_file_count"]
        == 3
    )

    assert (
        audit_result["metrics"]["findings_count"]
        == len(audit_result["findings"])
    )


def test_runtime_context_is_built_and_passed_to_architecture_plugin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_path = _create_python_project(tmp_path)
    captured: dict[str, Any] = {}

    def result_factory(
        plugin_context: dict[str, Any],
    ) -> dict[str, Any]:
        captured["plugin_context"] = dict(
            plugin_context
        )

        return _canonical_result(
            status=AuditStatus.COMPLETED,
            project_path=project_path,
        )

    monkeypatch.setattr(
        architecture_auditor,
        "run",
        _runner_for(result_factory),
    )

    options = {
        "ignored_directories": ["generated"],
        "require_package_initializers": True,
    }

    runtime, registry = _create_runtime(
        tmp_path=tmp_path,
        project_path=project_path,
        plugin_options=options,
    )

    context = runtime.context

    assert isinstance(context, RuntimeContext)
    assert context.registry is registry

    assert (
        context.audit.target_path
        == project_path.resolve()
    )

    assert context.session.audit is context.audit

    assert (
        context.get_metadata("kernel_version")
        == UAAFKernel.kernel_version
    )

    assert (
        context.get_metadata("test_suite")
        == "F"
    )

    assert (
        context.get_metadata(
            "integration_target"
        )
        == ARCHITECTURE_PLUGIN_ID
    )

    runtime.run()

    expected_plugin_context = {
        "project_path": str(
            project_path.resolve()
        ),
        "audit_type": "architecture",
        **options,
    }

    assert (
        captured["plugin_context"]
        == expected_plugin_context
    )

    assert (
        runtime.context.session.get_context(
            PLUGIN_INPUT_CONTEXT_KEY
        )
        == expected_plugin_context
    )


@pytest.mark.parametrize(
    (
        "audit_status",
        "findings",
        "expected_pipeline_status",
        "expected_processors_with_warnings",
    ),
    (
        (
            AuditStatus.COMPLETED,
            (),
            "completed",
            0,
        ),
        (
            AuditStatus.COMPLETED_WITH_FINDINGS,
            (_warning_finding(),),
            "completed_with_warnings",
            1,
        ),
    ),
    ids=(
        "completed",
        "completed-with-findings",
    ),
)
def test_pipeline_handles_successful_architecture_audit_statuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    audit_status: AuditStatus,
    findings: tuple[AuditFinding, ...],
    expected_pipeline_status: str,
    expected_processors_with_warnings: int,
) -> None:
    project_path = _create_python_project(tmp_path)

    monkeypatch.setattr(
        architecture_auditor,
        "run",
        _runner_for(
            lambda _context: _canonical_result(
                status=audit_status,
                project_path=project_path,
                findings=findings,
            )
        ),
    )

    runtime, _registry = _create_runtime(
        tmp_path=tmp_path,
        project_path=project_path,
    )

    processor_results = runtime.run()

    audit_result = _extract_audit_result(
        processor_results[0]
    )

    validate_audit_result(audit_result)

    assert (
        audit_result["status"]
        == audit_status.value
    )

    assert (
        runtime.context.get_metadata(
            "pipeline_status"
        )
        == expected_pipeline_status
    )

    assert (
        runtime.context.get_metric(
            "processors_executed"
        )
        == 1
    )

    assert (
        runtime.context.get_metric(
            "processors_succeeded"
        )
        == 1
    )

    assert (
        runtime.context.get_metric(
            "processors_failed"
        )
        == 0
    )

    assert (
        runtime.context.get_metric(
            "processors_with_warnings"
        )
        == expected_processors_with_warnings
    )


def test_pipeline_handles_failed_architecture_audit_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_path = _create_python_project(tmp_path)

    expected_result = _canonical_result(
        status=AuditStatus.FAILED,
        project_path=project_path,
        errors=(
            "Deterministic Architecture Auditor failure.",
        ),
    )

    monkeypatch.setattr(
        architecture_auditor,
        "run",
        _runner_for(
            lambda _context: expected_result
        ),
    )

    runtime, _registry = _create_runtime(
        tmp_path=tmp_path,
        project_path=project_path,
    )

    with pytest.raises(
        ArchitecturePluginExecutionError,
        match="terminal status 'failed'",
    ):
        runtime.run()

    preserved_result = runtime.context.session.get_context(
        PLUGIN_RESULT_CONTEXT_KEY
    )

    validate_audit_result(preserved_result)

    assert preserved_result == expected_result

    assert (
        runtime.context.get_metadata(
            "pipeline_status"
        )
        == "failed"
    )

    assert (
        runtime.context.get_metric(
            "processors_executed"
        )
        == 1
    )

    assert (
        runtime.context.get_metric(
            "processors_succeeded"
        )
        == 0
    )

    assert (
        runtime.context.get_metric(
            "processors_failed"
        )
        == 1
    )

    assert runtime.context.audit.status.value == "failed"
    assert runtime.context.session.status.value == "failed"
    assert runtime.is_terminal


def test_pipeline_preserves_canonical_contract_end_to_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_path = _create_python_project(tmp_path)
    finding = _warning_finding()

    expected_metrics = _architecture_metrics(
        findings_count=1,
        python_file_count=7,
        module_count=5,
        package_count=2,
    )

    expected_result = _canonical_result(
        status=AuditStatus.COMPLETED_WITH_FINDINGS,
        project_path=project_path,
        findings=(finding,),
        metrics=expected_metrics,
    )

    monkeypatch.setattr(
        architecture_auditor,
        "run",
        _runner_for(
            lambda _context: expected_result
        ),
    )

    runtime, _registry = _create_runtime(
        tmp_path=tmp_path,
        project_path=project_path,
    )

    processor_results = runtime.run()

    processor_audit_result = _extract_audit_result(
        processor_results[0]
    )

    session_audit_result = (
        runtime.context.session.get_context(
            PLUGIN_RESULT_CONTEXT_KEY
        )
    )

    validate_audit_result(
        processor_audit_result
    )

    validate_audit_result(
        session_audit_result
    )

    assert (
        processor_audit_result
        == expected_result
    )

    assert (
        session_audit_result
        == expected_result
    )

    assert processor_audit_result["execution"] == {
        "started_at": FIXED_STARTED_AT,
        "completed_at": FIXED_COMPLETED_AT,
        "duration_ms": FIXED_DURATION_MS,
    }

    assert (
        processor_audit_result["metrics"]
        == expected_metrics
    )

    assert processor_audit_result["findings"] == [
        finding.to_dict()
    ]

    assert (
        processor_audit_result[
            "metrics"
        ]["findings_count"]
        == len(
            processor_audit_result["findings"]
        )
    )

    pipeline_execution = (
        runtime.context.get_metadata(
            "pipeline_execution"
        )
    )

    assert (
        pipeline_execution["status"]
        == "completed_with_warnings"
    )

    assert (
        pipeline_execution[
            "executed_processor_ids"
        ]
        == [ARCHITECTURE_PLUGIN_ID]
    )

    assert (
        pipeline_execution[
            "failed_processor_ids"
        ]
        == []
    )

    assert (
        runtime.context.get_metric(
            "processors_expected"
        )
        == 1
    )

    assert (
        runtime.context.get_metric(
            "processors_executed"
        )
        == 1
    )

    assert (
        runtime.context.get_metric(
            "processors_succeeded"
        )
        == 1
    )

    assert (
        runtime.context.get_metric(
            "processors_failed"
        )
        == 0
    )