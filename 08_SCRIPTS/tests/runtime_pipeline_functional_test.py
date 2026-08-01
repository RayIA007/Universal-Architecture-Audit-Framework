"""
Functional test for the UAAF Runtime Pipeline.

Run from the UAAF project root:

    python 08_SCRIPTS/tests/runtime_pipeline_functional_test.py

The test validates:

- profile-based pipeline creation;
- stable processor order;
- dependency ordering;
- processor execution;
- warning propagation;
- runtime metrics;
- pipeline metadata;
- execution snapshots;
- cycle detection.

The test creates temporary output data under:

    07_OUTPUTS/runtime_pipeline_test

and removes any previous test directory before execution.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "08_SCRIPTS"

sys.path.insert(0, str(SCRIPTS_ROOT))

from uaaf_core.contracts.processor import ProcessorContract
from uaaf_core.models.audit import Audit
from uaaf_core.models.enums import AuditDomain, ComplianceLevel
from uaaf_core.models.profile import AuditProfile
from uaaf_core.models.session import AuditSession
from uaaf_core.registry import UAAFRegistry
from uaaf_core.runtime import (
    PipelineFailurePolicy,
    PipelineStatus,
    PipelineStep,
    RuntimeContext,
    RuntimePipeline,
)


class DocumentationProcessor(ProcessorContract):
    processor_id = "documentation-processor"
    processor_version = "1.0.0"
    processor_description = "Analyzes project documentation."

    def validate(self, session: AuditSession) -> None:
        if not session.is_open:
            raise RuntimeError("The audit session must be open.")

    def execute(self, session: AuditSession) -> None:
        self.add_output("documents_analyzed", 4)
        self.set_metadata("domain", "documentation")


class ArchitectureProcessor(ProcessorContract):
    processor_id = "architecture-processor"
    processor_version = "1.0.0"
    processor_description = "Analyzes project architecture."

    def validate(self, session: AuditSession) -> None:
        if not session.is_open:
            raise RuntimeError("The audit session must be open.")

    def execute(self, session: AuditSession) -> None:
        self.add_output("components_analyzed", 9)
        self.add_warning("One component has no architecture record.")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def build_context(test_root: Path) -> RuntimeContext:
    registry = UAAFRegistry()
    registry.register_processor(DocumentationProcessor)
    registry.register_processor(ArchitectureProcessor)

    profile = AuditProfile(
        profile_id="generic-project",
        name="Generic Project Audit",
        version="1.0.0",
        compliance_level=ComplianceLevel.CORE,
        domains=(
            AuditDomain.DOCUMENTATION,
            AuditDomain.ARCHITECTURE,
        ),
        processor_ids=(
            "documentation-processor",
            "architecture-processor",
        ),
    )
    registry.register_profile(profile)

    audit = Audit(
        target_path=PROJECT_ROOT,
        profile_id=profile.id,
        output_path=test_root / "outputs",
    )

    session = AuditSession(
        audit=audit,
        workspace_path=test_root / "workspace",
    )

    session.open()
    session.start()
    audit.mark_initializing()
    audit.mark_ready()
    audit.mark_running()

    context = RuntimeContext(
        audit=audit,
        session=session,
        profile=profile,
        registry=registry,
    )

    context.set_metric("processors_expected", 2)
    context.set_metric("processors_executed", 0)
    context.set_metric("processors_succeeded", 0)
    context.set_metric("processors_failed", 0)
    context.set_metric("processors_with_warnings", 0)

    return context


@pytest.fixture
def context(tmp_path: Path) -> RuntimeContext:
    """Build one isolated RuntimeContext for each pytest test."""

    # UAAF-PYTEST-CONTEXT-FIXTURE
    return build_context(
        tmp_path / "runtime_pipeline_functional_test"
    )


def test_profile_pipeline(context: RuntimeContext) -> None:
    pipeline = RuntimePipeline.from_context(context)

    ordered_ids = pipeline.validate(context)
    require(
        ordered_ids == (
            "documentation-processor",
            "architecture-processor",
        ),
        f"Unexpected profile order: {ordered_ids!r}",
    )

    execution = pipeline.execute(context)

    require(
        execution.status is PipelineStatus.COMPLETED_WITH_WARNINGS,
        f"Unexpected pipeline status: {execution.status!r}",
    )
    require(
        execution.executed_processor_ids == [
            "documentation-processor",
            "architecture-processor",
        ],
        "Unexpected executed processor order.",
    )
    require(
        not execution.failed_processor_ids,
        "No processor should have failed.",
    )
    require(
        not execution.skipped_processor_ids,
        "No processor should have been skipped.",
    )
    require(
        context.processor_result_count == 2,
        "RuntimeContext should contain two processor results.",
    )
    require(
        context.get_metric("processors_executed") == 2,
        "processors_executed must be 2.",
    )
    require(
        context.get_metric("processors_succeeded") == 2,
        "processors_succeeded must be 2.",
    )
    require(
        context.get_metric("processors_failed") == 0,
        "processors_failed must be 0.",
    )
    require(
        context.get_metric("processors_with_warnings") == 1,
        "processors_with_warnings must be 1.",
    )
    require(
        context.get_metadata("pipeline_status")
        == "completed_with_warnings",
        "Pipeline status metadata was not stored correctly.",
    )
    require(
        context.get_metadata("pipeline_id")
        == "generic-project-pipeline",
        "Pipeline identifier metadata was not stored correctly.",
    )

    print("[OK] Profile pipeline creation")
    print("[OK] Sequential processor execution")
    print("[OK] Warning propagation")
    print("[OK] Runtime metrics")
    print("[OK] Pipeline metadata and snapshot")


def test_dependency_order(context: RuntimeContext) -> None:
    pipeline = RuntimePipeline(
        pipeline_id="dependency-order-test",
        steps=(
            PipelineStep(
                processor_id="architecture-processor",
                depends_on=("documentation-processor",),
            ),
            PipelineStep(
                processor_id="documentation-processor",
            ),
        ),
        failure_policy=PipelineFailurePolicy.STOP_ON_ERROR,
    )

    ordered_ids = pipeline.validate(context)

    require(
        ordered_ids == (
            "documentation-processor",
            "architecture-processor",
        ),
        f"Dependency order was not resolved correctly: {ordered_ids!r}",
    )

    print("[OK] Stable dependency ordering")


def test_cycle_detection(context: RuntimeContext) -> None:
    pipeline = RuntimePipeline(
        pipeline_id="cycle-test",
        steps=(
            PipelineStep(
                processor_id="documentation-processor",
                depends_on=("architecture-processor",),
            ),
            PipelineStep(
                processor_id="architecture-processor",
                depends_on=("documentation-processor",),
            ),
        ),
    )

    try:
        pipeline.validate(context)
    except ValueError as error:
        require(
            "dependency cycle" in str(error).lower(),
            f"Unexpected cycle error: {error}",
        )
    else:
        raise AssertionError(
            "Pipeline dependency cycle was not detected."
        )

    print("[OK] Dependency cycle detection")


def main() -> int:
    test_root = PROJECT_ROOT / "07_OUTPUTS" / "runtime_pipeline_test"

    if test_root.exists():
        shutil.rmtree(test_root)

    test_root.mkdir(parents=True, exist_ok=True)

    execution_context = build_context(test_root)
    test_profile_pipeline(execution_context)

    dependency_context = build_context(test_root / "dependency")
    test_dependency_order(dependency_context)

    cycle_context = build_context(test_root / "cycle")
    test_cycle_detection(cycle_context)

    snapshot = execution_context.get_metadata("pipeline_execution")

    print()
    print("Pipeline ID:", snapshot["pipeline_id"])
    print("Pipeline status:", snapshot["status"])
    print(
        "Executed processors:",
        snapshot["executed_processor_ids"],
    )
    print(
        "Warning count:",
        len(snapshot["warnings"]),
    )
    print()
    print("[PASS] Runtime Pipeline functional test completed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())