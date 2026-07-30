"""
Pipeline execution subsystem for the Universal Architecture Audit Framework.

Responsible only for executing processor instances and storing their results.

It does not validate dependency graphs or orchestrate the pipeline lifecycle.
"""

from __future__ import annotations

from uaaf_core.contracts.processor import ProcessorResult
from uaaf_core.runtime.runtime_context import RuntimeContext


class PipelineExecutor:
    """
    Executes one processor at a time.
    """

    @staticmethod
    def execute_processor(
        *,
        context: RuntimeContext,
        processor_id: str,
    ) -> ProcessorResult:

        if context.has_processor_result(processor_id):
            raise ValueError(
                f"Processor {processor_id!r} has already been executed."
            )

        processor = context.registry.create_processor(
            processor_id
        )

        try:
            result = processor.run(context.session)

        except Exception:

            PipelineExecutor.capture_failed_result(
                context=context,
                processor_id=processor_id,
            )

            context.increment_metric(
                "processors_executed"
            )

            context.increment_metric(
                "processors_failed"
            )

            raise

        context.add_processor_result(result)

        context.increment_metric(
            "processors_executed"
        )

        context.increment_metric(
            "processors_succeeded"
        )

        if result.has_warnings:

            context.increment_metric(
                "processors_with_warnings"
            )

        return result

    @staticmethod
    def capture_failed_result(
        *,
        context: RuntimeContext,
        processor_id: str,
    ) -> None:

        result = context.session.get_context(
            f"processor_result:{processor_id}"
        )

        if isinstance(result, ProcessorResult):

            context.add_processor_result(
                result,
                replace=True,
            )


__all__ = [
    "PipelineExecutor",
]