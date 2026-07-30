"""
Pipeline dependency guard for the Universal Architecture Audit Framework.

Responsible only for deciding whether a processor must be skipped because
one of its declared dependencies failed or was skipped.
"""

from __future__ import annotations

from collections.abc import Iterable


class PipelineDependencyGuard:
    """Evaluate whether processor dependencies prevent execution."""

    @staticmethod
    def should_skip(
        *,
        dependencies: Iterable[str],
        failed_processor_ids: Iterable[str],
        skipped_processor_ids: Iterable[str],
    ) -> bool:
        """
        Return whether any dependency failed or was previously skipped.

        The guard is intentionally independent from RuntimePipeline models so
        it can be reused without introducing circular imports.
        """
        failed = set(failed_processor_ids)
        skipped = set(skipped_processor_ids)

        return any(
            dependency in failed or dependency in skipped
            for dependency in dependencies
        )


__all__ = [
    "PipelineDependencyGuard",
]
