"""
Pipeline metrics and metadata subsystem for the Universal Architecture Audit
Framework.

This module prepares RuntimeContext before pipeline execution and records the
final execution state after completion.

It does not execute processors or resolve dependencies.
"""

from __future__ import annotations

from uaaf_core.runtime.pipeline_models import PipelineExecution
from uaaf_core.runtime.runtime_context import RuntimeContext


class PipelineMetrics:
    """
    Manage pipeline metadata and execution metrics in RuntimeContext.
    """

    @staticmethod
    def prepare(
        *,
        context: RuntimeContext,
        pipeline_id: str,
        pipeline_version: str,
        failure_policy: str,
        ordered_processor_ids: tuple[str, ...],
    ) -> None:
        """
        Initialize pipeline metadata and counters before execution.
        """
        context.set_metadata(
            "pipeline_id",
            pipeline_id,
        )
        context.set_metadata(
            "pipeline_version",
            pipeline_version,
        )
        context.set_metadata(
            "pipeline_failure_policy",
            failure_policy,
        )
        context.set_metric(
            "processors_expected",
            len(ordered_processor_ids),
        )

        for metric_name in (
            "processors_executed",
            "processors_succeeded",
            "processors_failed",
            "processors_with_warnings",
        ):
            if context.get_metric(metric_name) is None:
                context.set_metric(metric_name, 0)

    @staticmethod
    def finalize(
        *,
        context: RuntimeContext,
        execution: PipelineExecution,
    ) -> None:
        """
        Store final pipeline state and calculated execution metrics.
        """
        context.set_metadata(
            "pipeline_status",
            execution.status.value,
        )
        context.set_metadata(
            "pipeline_execution",
            execution.snapshot(),
        )
        context.set_metric(
            "pipeline_duration_seconds",
            execution.duration_seconds or 0.0,
        )
        context.set_metric(
            "processors_skipped",
            len(execution.skipped_processor_ids),
        )


__all__ = [
    "PipelineMetrics",
]