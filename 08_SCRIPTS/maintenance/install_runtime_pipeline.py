"""
Install the UAAF Runtime Pipeline subsystem.

Run from the UAAF project root:

    python 08_SCRIPTS/maintenance/install_runtime_pipeline.py

The installer:
- creates or replaces runtime/pipeline.py;
- updates runtime/__init__.py exports automatically;
- creates timestamped backups;
- validates all modified Python files;
- restores backups if validation fails;
- is safe to run repeatedly.
"""

from __future__ import annotations

import ast
import py_compile
import shutil
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = PROJECT_ROOT / "08_SCRIPTS" / "uaaf_core" / "runtime"
PIPELINE_FILE = RUNTIME_DIR / "pipeline.py"
INIT_FILE = RUNTIME_DIR / "__init__.py"

PIPELINE_SOURCE = '"""\nSequential pipeline subsystem for the Universal Architecture Audit Framework.\n\nThis module defines the deterministic v1.0 pipeline used to validate, order,\nand execute processors declared by an AuditProfile.\n\nThe pipeline operates on RuntimeContext. It does not own the Kernel, discover\nplugins, generate reports, or implement parallel execution.\n"""\n\nfrom __future__ import annotations\n\nfrom collections import defaultdict, deque\nfrom dataclasses import dataclass, field\nfrom datetime import UTC, datetime\nfrom enum import Enum\nfrom threading import RLock\nfrom typing import Any, Iterable\n\nfrom uaaf_core.contracts.processor import ProcessorResult\nfrom uaaf_core.runtime.runtime_context import RuntimeContext\n\n\nclass PipelineStatus(str, Enum):\n    """Lifecycle status of one pipeline execution."""\n\n    CREATED = "created"\n    VALIDATING = "validating"\n    READY = "ready"\n    RUNNING = "running"\n    COMPLETED = "completed"\n    COMPLETED_WITH_WARNINGS = "completed_with_warnings"\n    FAILED = "failed"\n    CANCELLED = "cancelled"\n\n\nclass PipelineFailurePolicy(str, Enum):\n    """Policy applied when one processor raises an exception."""\n\n    STOP_ON_ERROR = "stop_on_error"\n    CONTINUE_ON_ERROR = "continue_on_error"\n\n\n@dataclass(frozen=True, slots=True)\nclass PipelineStep:\n    """\n    Immutable declaration of one processor execution step.\n\n    Attributes:\n        processor_id:\n            Registered processor identifier.\n        depends_on:\n            Processor identifiers that must execute before this step.\n        enabled:\n            Whether the step participates in execution.\n        required:\n            Whether failure of this step makes the pipeline unsuccessful.\n        metadata:\n            Immutable-by-convention step metadata.\n    """\n\n    processor_id: str\n    depends_on: tuple[str, ...] = ()\n    enabled: bool = True\n    required: bool = True\n    metadata: dict[str, Any] = field(default_factory=dict)\n\n    def __post_init__(self) -> None:\n        normalized_id = self._normalize_identifier(\n            self.processor_id,\n            "processor_id",\n        )\n        normalized_dependencies = tuple(\n            self._normalize_identifier(value, "dependency")\n            for value in self.depends_on\n        )\n\n        if normalized_id in normalized_dependencies:\n            raise ValueError(\n                f"Pipeline step {normalized_id!r} cannot depend on itself."\n            )\n\n        if len(set(normalized_dependencies)) != len(\n            normalized_dependencies\n        ):\n            raise ValueError(\n                f"Pipeline step {normalized_id!r} contains duplicate "\n                "dependencies."\n            )\n\n        if not isinstance(self.enabled, bool):\n            raise TypeError("PipelineStep enabled must be a bool.")\n\n        if not isinstance(self.required, bool):\n            raise TypeError("PipelineStep required must be a bool.")\n\n        if not isinstance(self.metadata, dict):\n            raise TypeError("PipelineStep metadata must be a dictionary.")\n\n        object.__setattr__(self, "processor_id", normalized_id)\n        object.__setattr__(self, "depends_on", normalized_dependencies)\n        object.__setattr__(self, "metadata", dict(self.metadata))\n\n    @staticmethod\n    def _normalize_identifier(value: str, field_name: str) -> str:\n        if not isinstance(value, str):\n            raise TypeError(\n                f"PipelineStep {field_name} must be a string, "\n                f"received {type(value).__name__}."\n            )\n\n        normalized = value.strip()\n        if not normalized:\n            raise ValueError(\n                f"PipelineStep {field_name} cannot be empty."\n            )\n\n        return normalized\n\n\n@dataclass(slots=True)\nclass PipelineExecution:\n    """Execution record produced by RuntimePipeline."""\n\n    pipeline_id: str\n    status: PipelineStatus = PipelineStatus.CREATED\n    started_at: datetime | None = None\n    completed_at: datetime | None = None\n    ordered_processor_ids: tuple[str, ...] = ()\n    executed_processor_ids: list[str] = field(default_factory=list)\n    skipped_processor_ids: list[str] = field(default_factory=list)\n    failed_processor_ids: list[str] = field(default_factory=list)\n    warnings: list[str] = field(default_factory=list)\n    errors: list[str] = field(default_factory=list)\n\n    @property\n    def duration_seconds(self) -> float | None:\n        """Return elapsed execution time when available."""\n        if self.started_at is None:\n            return None\n\n        endpoint = self.completed_at or datetime.now(UTC)\n        return max(\n            0.0,\n            (endpoint - self.started_at).total_seconds(),\n        )\n\n    @property\n    def succeeded(self) -> bool:\n        """Return whether execution completed successfully."""\n        return self.status in {\n            PipelineStatus.COMPLETED,\n            PipelineStatus.COMPLETED_WITH_WARNINGS,\n        }\n\n    @property\n    def has_warnings(self) -> bool:\n        return bool(self.warnings)\n\n    @property\n    def has_errors(self) -> bool:\n        return bool(self.errors)\n\n    def snapshot(self) -> dict[str, Any]:\n        """Return a serializable execution summary."""\n        return {\n            "pipeline_id": self.pipeline_id,\n            "status": self.status.value,\n            "started_at": (\n                self.started_at.isoformat()\n                if self.started_at is not None\n                else None\n            ),\n            "completed_at": (\n                self.completed_at.isoformat()\n                if self.completed_at is not None\n                else None\n            ),\n            "duration_seconds": self.duration_seconds,\n            "ordered_processor_ids": list(\n                self.ordered_processor_ids\n            ),\n            "executed_processor_ids": list(\n                self.executed_processor_ids\n            ),\n            "skipped_processor_ids": list(\n                self.skipped_processor_ids\n            ),\n            "failed_processor_ids": list(\n                self.failed_processor_ids\n            ),\n            "warnings": list(self.warnings),\n            "errors": list(self.errors),\n        }\n\n\nclass RuntimePipeline:\n    """\n    Validate, order, and execute processor steps for one RuntimeContext.\n\n    Version 1.0 uses deterministic sequential execution. Dependency ordering\n    is resolved through a stable topological sort that preserves declaration\n    order whenever possible.\n    """\n\n    pipeline_version = "1.0.0"\n\n    def __init__(\n        self,\n        *,\n        pipeline_id: str,\n        steps: Iterable[PipelineStep],\n        failure_policy: PipelineFailurePolicy = (\n            PipelineFailurePolicy.STOP_ON_ERROR\n        ),\n    ) -> None:\n        self._pipeline_id = self._normalize_identifier(\n            pipeline_id,\n            "pipeline identifier",\n        )\n        self._steps = tuple(steps)\n\n        if not self._steps:\n            raise ValueError(\n                "RuntimePipeline requires at least one step."\n            )\n\n        if not all(\n            isinstance(step, PipelineStep)\n            for step in self._steps\n        ):\n            raise TypeError(\n                "RuntimePipeline steps must contain only PipelineStep "\n                "instances."\n            )\n\n        if not isinstance(failure_policy, PipelineFailurePolicy):\n            raise TypeError(\n                "RuntimePipeline failure_policy must be a "\n                "PipelineFailurePolicy."\n            )\n\n        self._failure_policy = failure_policy\n        self._lock = RLock()\n        self._validate_unique_steps()\n\n    @property\n    def pipeline_id(self) -> str:\n        return self._pipeline_id\n\n    @property\n    def steps(self) -> tuple[PipelineStep, ...]:\n        return self._steps\n\n    @property\n    def failure_policy(self) -> PipelineFailurePolicy:\n        return self._failure_policy\n\n    @classmethod\n    def from_context(\n        cls,\n        context: RuntimeContext,\n        *,\n        pipeline_id: str | None = None,\n        failure_policy: PipelineFailurePolicy = (\n            PipelineFailurePolicy.STOP_ON_ERROR\n        ),\n    ) -> "RuntimePipeline":\n        """\n        Build a sequential pipeline from the active profile.\n\n        Profile processor order becomes declaration order. No dependencies are\n        inferred because ProcessorContract v1.0 does not yet declare them.\n        """\n        if not isinstance(context, RuntimeContext):\n            raise TypeError(\n                "RuntimePipeline context must be a RuntimeContext."\n            )\n\n        steps = tuple(\n            PipelineStep(processor_id=processor_id)\n            for processor_id in context.profile.processor_ids\n        )\n\n        return cls(\n            pipeline_id=(\n                pipeline_id\n                or f"{context.profile_id}-pipeline"\n            ),\n            steps=steps,\n            failure_policy=failure_policy,\n        )\n\n    def validate(\n        self,\n        context: RuntimeContext,\n    ) -> tuple[str, ...]:\n        """\n        Validate the pipeline against one RuntimeContext.\n\n        Returns:\n            Deterministically ordered enabled processor identifiers.\n        """\n        if not isinstance(context, RuntimeContext):\n            raise TypeError(\n                "RuntimePipeline context must be a RuntimeContext."\n            )\n\n        enabled_steps = tuple(\n            step for step in self._steps if step.enabled\n        )\n\n        if not enabled_steps:\n            raise RuntimeError(\n                f"Pipeline {self.pipeline_id!r} has no enabled steps."\n            )\n\n        declared_ids = {\n            step.processor_id for step in self._steps\n        }\n\n        for step in enabled_steps:\n            if not context.profile.requires_processor(\n                step.processor_id\n            ):\n                raise ValueError(\n                    f"Processor {step.processor_id!r} is not declared by "\n                    f"profile {context.profile_id!r}."\n                )\n\n            if not context.registry.has_processor(\n                step.processor_id\n            ):\n                raise RuntimeError(\n                    f"Processor {step.processor_id!r} is not registered."\n                )\n\n            missing_dependencies = tuple(\n                dependency\n                for dependency in step.depends_on\n                if dependency not in declared_ids\n            )\n\n            if missing_dependencies:\n                raise ValueError(\n                    f"Pipeline step {step.processor_id!r} references "\n                    f"unknown dependencies: "\n                    f"{\', \'.join(missing_dependencies)}."\n                )\n\n        return self._stable_topological_order(enabled_steps)\n\n    def execute(\n        self,\n        context: RuntimeContext,\n    ) -> PipelineExecution:\n        """\n        Execute all enabled steps sequentially.\n\n        Processor results are stored in RuntimeContext. Metrics use the same\n        keys already established by UAAFRuntime.\n        """\n        with self._lock:\n            execution = PipelineExecution(\n                pipeline_id=self.pipeline_id\n            )\n            execution.status = PipelineStatus.VALIDATING\n\n            ordered_ids = self.validate(context)\n            execution.ordered_processor_ids = ordered_ids\n            execution.status = PipelineStatus.READY\n\n            self._prepare_context(context, ordered_ids)\n\n            execution.started_at = datetime.now(UTC)\n            execution.status = PipelineStatus.RUNNING\n\n            step_map = {\n                step.processor_id: step\n                for step in self._steps\n            }\n\n            for processor_id in ordered_ids:\n                step = step_map[processor_id]\n\n                if self._dependency_failed(\n                    step=step,\n                    execution=execution,\n                ):\n                    execution.skipped_processor_ids.append(\n                        processor_id\n                    )\n                    warning = (\n                        f"Processor {processor_id!r} was skipped because "\n                        "one or more dependencies failed."\n                    )\n                    execution.warnings.append(warning)\n                    context.session.add_warning(warning)\n                    continue\n\n                try:\n                    result = self._execute_step(\n                        context=context,\n                        processor_id=processor_id,\n                    )\n                except Exception as error:\n                    execution.failed_processor_ids.append(\n                        processor_id\n                    )\n                    execution.executed_processor_ids.append(\n                        processor_id\n                    )\n\n                    message = (\n                        f"Processor {processor_id!r} failed: "\n                        f"{type(error).__name__}: {str(error).strip()}"\n                    )\n                    execution.errors.append(message)\n\n                    if (\n                        step.required\n                        and self.failure_policy\n                        is PipelineFailurePolicy.STOP_ON_ERROR\n                    ):\n                        execution.status = PipelineStatus.FAILED\n                        execution.completed_at = datetime.now(UTC)\n                        self._finalize_context(\n                            context=context,\n                            execution=execution,\n                        )\n                        raise\n\n                    continue\n\n                execution.executed_processor_ids.append(\n                    processor_id\n                )\n\n                if result.has_warnings:\n                    execution.warnings.extend(result.warnings)\n\n            execution.completed_at = datetime.now(UTC)\n\n            if execution.failed_processor_ids:\n                required_failed = any(\n                    step_map[processor_id].required\n                    for processor_id\n                    in execution.failed_processor_ids\n                )\n                execution.status = (\n                    PipelineStatus.FAILED\n                    if required_failed\n                    else PipelineStatus.COMPLETED_WITH_WARNINGS\n                )\n            elif execution.has_warnings:\n                execution.status = (\n                    PipelineStatus.COMPLETED_WITH_WARNINGS\n                )\n            else:\n                execution.status = PipelineStatus.COMPLETED\n\n            self._finalize_context(\n                context=context,\n                execution=execution,\n            )\n            return execution\n\n    def snapshot(self) -> dict[str, Any]:\n        """Return a serializable pipeline definition."""\n        return {\n            "pipeline_id": self.pipeline_id,\n            "pipeline_version": self.pipeline_version,\n            "failure_policy": self.failure_policy.value,\n            "steps": [\n                {\n                    "processor_id": step.processor_id,\n                    "depends_on": list(step.depends_on),\n                    "enabled": step.enabled,\n                    "required": step.required,\n                    "metadata": dict(step.metadata),\n                }\n                for step in self.steps\n            ],\n        }\n\n    def _execute_step(\n        self,\n        *,\n        context: RuntimeContext,\n        processor_id: str,\n    ) -> ProcessorResult:\n        if context.has_processor_result(processor_id):\n            raise ValueError(\n                f"Processor {processor_id!r} has already been executed."\n            )\n\n        processor = context.registry.create_processor(\n            processor_id\n        )\n\n        try:\n            result = processor.run(context.session)\n        except Exception:\n            self._capture_failed_result(\n                context=context,\n                processor_id=processor_id,\n            )\n            context.increment_metric("processors_executed")\n            context.increment_metric("processors_failed")\n            raise\n\n        context.add_processor_result(result)\n        context.increment_metric("processors_executed")\n        context.increment_metric("processors_succeeded")\n\n        if result.has_warnings:\n            context.increment_metric(\n                "processors_with_warnings"\n            )\n\n        return result\n\n    @staticmethod\n    def _capture_failed_result(\n        *,\n        context: RuntimeContext,\n        processor_id: str,\n    ) -> None:\n        result = context.session.get_context(\n            f"processor_result:{processor_id}"\n        )\n\n        if isinstance(result, ProcessorResult):\n            context.add_processor_result(\n                result,\n                replace=True,\n            )\n\n    @staticmethod\n    def _dependency_failed(\n        *,\n        step: PipelineStep,\n        execution: PipelineExecution,\n    ) -> bool:\n        failed = set(execution.failed_processor_ids)\n        skipped = set(execution.skipped_processor_ids)\n\n        return any(\n            dependency in failed or dependency in skipped\n            for dependency in step.depends_on\n        )\n\n    def _prepare_context(\n        self,\n        context: RuntimeContext,\n        ordered_ids: tuple[str, ...],\n    ) -> None:\n        context.set_metadata(\n            "pipeline_id",\n            self.pipeline_id,\n        )\n        context.set_metadata(\n            "pipeline_version",\n            self.pipeline_version,\n        )\n        context.set_metadata(\n            "pipeline_failure_policy",\n            self.failure_policy.value,\n        )\n        context.set_metric(\n            "processors_expected",\n            len(ordered_ids),\n        )\n\n        for metric_name in (\n            "processors_executed",\n            "processors_succeeded",\n            "processors_failed",\n            "processors_with_warnings",\n        ):\n            if context.get_metric(metric_name) is None:\n                context.set_metric(metric_name, 0)\n\n    @staticmethod\n    def _finalize_context(\n        *,\n        context: RuntimeContext,\n        execution: PipelineExecution,\n    ) -> None:\n        context.set_metadata(\n            "pipeline_status",\n            execution.status.value,\n        )\n        context.set_metadata(\n            "pipeline_execution",\n            execution.snapshot(),\n        )\n        context.set_metric(\n            "pipeline_duration_seconds",\n            execution.duration_seconds or 0.0,\n        )\n        context.set_metric(\n            "processors_skipped",\n            len(execution.skipped_processor_ids),\n        )\n\n    def _validate_unique_steps(self) -> None:\n        processor_ids = [\n            step.processor_id for step in self._steps\n        ]\n\n        if len(set(processor_ids)) != len(processor_ids):\n            duplicates = sorted(\n                processor_id\n                for processor_id in set(processor_ids)\n                if processor_ids.count(processor_id) > 1\n            )\n            raise ValueError(\n                "RuntimePipeline contains duplicate processor steps: "\n                f"{\', \'.join(duplicates)}."\n            )\n\n    @staticmethod\n    def _stable_topological_order(\n        steps: tuple[PipelineStep, ...],\n    ) -> tuple[str, ...]:\n        declaration_order = {\n            step.processor_id: index\n            for index, step in enumerate(steps)\n        }\n        enabled_ids = set(declaration_order)\n\n        indegree = {\n            step.processor_id: 0\n            for step in steps\n        }\n        dependents: dict[str, list[str]] = defaultdict(list)\n\n        for step in steps:\n            for dependency in step.depends_on:\n                if dependency not in enabled_ids:\n                    raise ValueError(\n                        f"Enabled processor {step.processor_id!r} depends "\n                        f"on disabled processor {dependency!r}."\n                    )\n\n                indegree[step.processor_id] += 1\n                dependents[dependency].append(step.processor_id)\n\n        ready = deque(\n            sorted(\n                (\n                    processor_id\n                    for processor_id, degree\n                    in indegree.items()\n                    if degree == 0\n                ),\n                key=declaration_order.get,\n            )\n        )\n        ordered: list[str] = []\n\n        while ready:\n            processor_id = ready.popleft()\n            ordered.append(processor_id)\n\n            newly_ready: list[str] = []\n\n            for dependent_id in dependents[processor_id]:\n                indegree[dependent_id] -= 1\n                if indegree[dependent_id] == 0:\n                    newly_ready.append(dependent_id)\n\n            for dependent_id in sorted(\n                newly_ready,\n                key=declaration_order.get,\n            ):\n                ready.append(dependent_id)\n\n        if len(ordered) != len(steps):\n            cyclic_ids = sorted(\n                processor_id\n                for processor_id, degree\n                in indegree.items()\n                if degree > 0\n            )\n            raise ValueError(\n                "RuntimePipeline contains a dependency cycle involving: "\n                f"{\', \'.join(cyclic_ids)}."\n            )\n\n        return tuple(ordered)\n\n    @staticmethod\n    def _normalize_identifier(\n        value: str,\n        field_name: str,\n    ) -> str:\n        if not isinstance(value, str):\n            raise TypeError(\n                f"RuntimePipeline {field_name} must be a string, "\n                f"received {type(value).__name__}."\n            )\n\n        normalized = value.strip()\n        if not normalized:\n            raise ValueError(\n                f"RuntimePipeline {field_name} cannot be empty."\n            )\n\n        return normalized\n\n\n__all__ = [\n    "PipelineExecution",\n    "PipelineFailurePolicy",\n    "PipelineStatus",\n    "PipelineStep",\n    "RuntimePipeline",\n]\n'


class InstallError(RuntimeError):
    pass


def backup(path: Path) -> Path | None:
    if not path.exists():
        return None

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = path.with_name(f"{path.name}.{stamp}.bak")
    shutil.copy2(path, destination)
    return destination


def ensure_runtime_exports(source: str) -> str:
    import_line = (
        "from uaaf_core.runtime.pipeline import (\n"
        "    PipelineExecution,\n"
        "    PipelineFailurePolicy,\n"
        "    PipelineStatus,\n"
        "    PipelineStep,\n"
        "    RuntimePipeline,\n"
        ")\n"
    )

    names = [
        "PipelineExecution",
        "PipelineFailurePolicy",
        "PipelineStatus",
        "PipelineStep",
        "RuntimePipeline",
    ]

    if "from uaaf_core.runtime.pipeline import" not in source:
        insertion = 0
        lines = source.splitlines(keepends=True)

        for index, line in enumerate(lines):
            if line.startswith("from uaaf_core.runtime."):
                insertion = index
                break
        else:
            insertion = len(lines)

        lines.insert(insertion, import_line)
        source = "".join(lines)

    tree = ast.parse(source)

    assign = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name)
                and target.id == "__all__"
                for target in node.targets
            ):
                assign = node
                break

    if assign is None:
        suffix = "\n__all__ = [\n"
        suffix += "".join(f'    "{name}",\n' for name in names)
        suffix += "]\n"
        return source.rstrip() + "\n" + suffix

    existing = []
    if isinstance(assign.value, (ast.List, ast.Tuple)):
        for element in assign.value.elts:
            if (
                isinstance(element, ast.Constant)
                and isinstance(element.value, str)
            ):
                existing.append(element.value)

    merged = existing + [
        name for name in names if name not in existing
    ]

    lines = source.splitlines(keepends=True)
    start = assign.lineno - 1
    end = assign.end_lineno
    replacement = ["__all__ = [\n"]
    replacement.extend(f'    "{name}",\n' for name in merged)
    replacement.append("]\n")
    lines[start:end] = replacement
    return "".join(lines)


def validate(path: Path) -> None:
    py_compile.compile(str(path), doraise=True)


def main() -> int:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    pipeline_backup = backup(PIPELINE_FILE)
    init_backup = backup(INIT_FILE)

    original_pipeline = (
        PIPELINE_FILE.read_bytes()
        if PIPELINE_FILE.exists()
        else None
    )
    original_init = (
        INIT_FILE.read_bytes()
        if INIT_FILE.exists()
        else None
    )

    try:
        PIPELINE_FILE.write_text(
            PIPELINE_SOURCE,
            encoding="utf-8",
            newline="\n",
        )

        init_source = (
            INIT_FILE.read_text(encoding="utf-8")
            if INIT_FILE.exists()
            else '"""UAAF runtime subsystem."""\n'
        )
        INIT_FILE.write_text(
            ensure_runtime_exports(init_source),
            encoding="utf-8",
            newline="\n",
        )

        validate(PIPELINE_FILE)
        validate(INIT_FILE)

    except Exception as error:
        if original_pipeline is None:
            PIPELINE_FILE.unlink(missing_ok=True)
        else:
            PIPELINE_FILE.write_bytes(original_pipeline)

        if original_init is None:
            INIT_FILE.unlink(missing_ok=True)
        else:
            INIT_FILE.write_bytes(original_init)

        print(f"[ROLLBACK] Installation reverted: {error}", file=sys.stderr)
        return 1

    print("[OK] Runtime Pipeline installed.")
    print(f"[OK] Pipeline file: {PIPELINE_FILE}")
    print(f"[OK] Runtime exports updated: {INIT_FILE}")

    if pipeline_backup:
        print(f"[OK] Pipeline backup: {pipeline_backup}")
    if init_backup:
        print(f"[OK] __init__ backup: {init_backup}")

    print("[OK] Python compilation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())