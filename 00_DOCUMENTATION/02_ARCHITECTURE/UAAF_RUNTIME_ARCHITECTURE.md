# UAAF Runtime Architecture
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-ARC-002
**Version:** 2.0
**Status:** Maintained
**Classification:** Architecture
**Owner:** Architecture

---

## 1. Purpose

Define how the current unified UAAF execution uses the existing kernel/runtime infrastructure.

## 2. Runtime Relationship to the Unified Orchestrator

`UnifiedOrchestrator.run_resolved()` is the current top-level execution coordinator.

For one resolved execution it:

1. validates execution paths;
2. discovers and selects plugins through `UAAFRegistry`;
3. builds isolated plugin contexts;
4. creates a temporary runtime workspace;
5. adapts each selected plugin to a `ProcessorContract`;
6. creates a runtime profile describing the selected processors/plugins;
7. asks `UAAFKernel` to create `UAAFRuntime`;
8. executes the runtime sequentially;
9. extracts ordered plugin `AuditResult` data;
10. consolidates results;
11. writes requested reports;
12. determines the process exit code.

## 3. UAAFRuntime Lifecycle

The underlying runtime lifecycle is:

```text
initialize
  -> start
  -> execute profile processors
  -> complete
```

A runtime failure transitions the runtime/session to failure handling before the exception is re-raised to the appropriate caller.

## 4. RuntimeContext

The runtime owns one `RuntimeContext`.

It carries the audit/session/profile/registry relationships, processor results, runtime metadata, metrics, paths, and shared/session state required by the runtime infrastructure.

The plugin context passed to `run(context)` is a separate filtered dictionary built by the orchestrator.

## 5. Dynamic Auditor Processor Adapter

Each selected plugin is wrapped by a runtime `ProcessorContract` type.

The adapter:

- validates that an isolated plugin context exists;
- calls the validated plugin runner;
- validates the returned audit-result mapping;
- converts an unexpected plugin exception into a canonical failed `AuditResult`;
- stores the audit result in runtime/session output state.

This preserves the existing runtime processor model while supporting dynamically discovered auditors.

## 6. Failure Behavior

Plugin execution failure does not require inventing a partial successful result.

The orchestrator/runtime records a canonical failed result with execution error information.

Final exit-code rules are:

```text
plugin/runtime/configuration failure -> 2
matching fail_on finding             -> 1
otherwise                            -> 0
```

Execution failure has priority.

## 7. Sequential Execution

Selected plugins are executed sequentially in deterministic selected order.

Parallel, asynchronous, or multiprocess orchestration is not a current feature.

## 8. Runtime Outputs

The unified runtime produces ordered per-plugin canonical results for the orchestrator.

The orchestrator then produces:

- one consolidated canonical result;
- requested report paths;
- runtime context;
- final exit code.

## 9. Historical Clarification

The previous runtime architecture document described mandatory stages for profile loading, rule loading, evidence collection, score calculation, and a fixed eleven-stage pipeline.

That model is not the current unified CLI contract and is superseded by this revision.

---
# End of Document
