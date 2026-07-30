"""
Dependency resolution subsystem for the Universal Architecture Audit Framework.

This module is responsible only for validating processor dependencies and
producing a deterministic execution order.

It does not execute processors, access RuntimeContext, update metrics, or
interact with the runtime.
"""

from __future__ import annotations

from collections import defaultdict, deque

from uaaf_core.runtime.pipeline_models import PipelineStep


class DependencyResolver:
    """
    Resolve processor execution order using a stable topological sort.
    """

    @staticmethod
    def resolve(
        steps: tuple[PipelineStep, ...],
    ) -> tuple[str, ...]:
        """
        Return processor identifiers in deterministic execution order.
        """
        declaration_order = {
            step.processor_id: index
            for index, step in enumerate(steps)
        }

        enabled_ids = set(declaration_order)

        indegree = {
            step.processor_id: 0
            for step in steps
        }

        dependents: dict[str, list[str]] = defaultdict(list)

        for step in steps:

            for dependency in step.depends_on:

                if dependency not in enabled_ids:
                    raise ValueError(
                        f"Enabled processor "
                        f"{step.processor_id!r} depends on "
                        f"disabled processor "
                        f"{dependency!r}."
                    )

                indegree[step.processor_id] += 1
                dependents[dependency].append(
                    step.processor_id
                )

        ready = deque(
            sorted(
                (
                    processor_id
                    for processor_id, degree
                    in indegree.items()
                    if degree == 0
                ),
                key=declaration_order.get,
            )
        )

        ordered: list[str] = []

        while ready:

            processor_id = ready.popleft()

            ordered.append(processor_id)

            newly_ready: list[str] = []

            for dependent_id in dependents[processor_id]:

                indegree[dependent_id] -= 1

                if indegree[dependent_id] == 0:
                    newly_ready.append(dependent_id)

            for dependent_id in sorted(
                newly_ready,
                key=declaration_order.get,
            ):
                ready.append(dependent_id)

        if len(ordered) != len(steps):

            cyclic_ids = sorted(
                processor_id
                for processor_id, degree
                in indegree.items()
                if degree > 0
            )

            raise ValueError(
                "RuntimePipeline contains a dependency "
                "cycle involving: "
                f"{', '.join(cyclic_ids)}."
            )

        return tuple(ordered)


__all__ = [
    "DependencyResolver",
]