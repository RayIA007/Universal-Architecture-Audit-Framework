"""
Pipeline execution result builder for the Universal Architecture Audit Framework.

Responsible for constructing the final PipelineExecution object from the
RuntimeContext after pipeline execution.

This module contains no execution logic.
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime

from uaaf_core.runtime.pipeline_models import (
    PipelineExecution,
    PipelineStatus,
)
from uaaf_core.runtime.runtime_context import RuntimeContext


class PipelineResultBuilder:
    """
    Builds the PipelineExecution object from RuntimeContext.
    """

    @staticmethod
    def create(
        *,
        context: RuntimeContext,
        pipeline_id: str,
        ordered_processor_ids: tuple[str, ...],
        started_at: datetime,
    ) -> PipelineExecution:

        completed_at = datetime.now(UTC)

        executed = []
        skipped = []
        failed = []
        warnings = []
        errors = []

        for processor_id in ordered_processor_ids:

            result = context.get_processor_result(
                processor_id
            )

            if result is None:

                skipped.append(processor_id)
                continue

            executed.append(processor_id)

            if not result.succeeded:
                failed.append(processor_id)

            warnings.extend(result.warnings)
            errors.extend(result.errors)

        if failed:

            status = PipelineStatus.FAILED

        elif warnings:

            status = (
                PipelineStatus
                .COMPLETED_WITH_WARNINGS
            )

        else:

            status = PipelineStatus.COMPLETED

        return PipelineExecution(
            pipeline_id=pipeline_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            ordered_processor_ids=ordered_processor_ids,
            executed_processor_ids=executed,
            skipped_processor_ids=skipped,
            failed_processor_ids=failed,
            warnings=warnings,
            errors=errors,
        )


__all__ = [
    "PipelineResultBuilder",
]