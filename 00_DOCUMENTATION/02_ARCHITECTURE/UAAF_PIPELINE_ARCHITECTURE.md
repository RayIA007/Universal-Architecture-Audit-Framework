# UAAF Pipeline Architecture
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-ARC-004
**Version:** 1.0
**Status:** Maintained
**Classification:** Architecture
**Owner:** Architecture

---

## 1. Purpose

Define the canonical end-to-end pipeline for one current UAAF CLI execution.

## 2. Pipeline

```text
CLI input
  -> explicit CLI-field detection
  -> global configuration resolution
  -> ResolvedConfig
  -> plugin discovery
  -> plugin selection
  -> plugin-specific configuration validation
  -> isolated plugin contexts
  -> runtime construction
  -> sequential processor/plugin execution
  -> ordered plugin results
  -> consolidated AuditResult
  -> report generation
  -> exit-code decision
```

## 3. Configuration Stage

Inputs may come from:

- framework defaults;
- optional configuration file;
- explicit CLI options.

Ordinary precedence:

```text
defaults < config file < explicit CLI
```

Exclusions are merged rather than replaced.

## 4. Discovery and Selection Stage

`UAAFRegistry` scans the configured plugin directory, validates candidate structure/metadata/runner contracts, registers valid descriptors in deterministic order, and resolves selectors.

`all` selects all registered auditors and cannot be mixed with explicit selectors.

## 5. Context Projection Stage

For each selected plugin the orchestrator builds an isolated context containing required framework values and only supported plugin configuration fields.

`project_path` and `audit_type` are reserved framework fields.

## 6. Runtime Stage

Selected plugins are represented as runtime processors and executed sequentially through the existing runtime/kernel infrastructure.

Each plugin call returns or is converted to canonical `AuditResult` data.

## 7. Consolidation Stage

The orchestrator validates each plugin result and builds one consolidated `AuditResult`.

Consolidated findings preserve source plugin/audit type in finding details where needed.

## 8. Reporting Stage

For each requested format:

- `markdown` -> human-readable report;
- `json` -> canonical machine-readable report;
- `sarif` -> SARIF 2.1.0 interoperability projection.

Default formats are `markdown,json`.

## 9. Exit Stage

```text
execution/plugin failure -> 2
fail_on severity matched -> 1
otherwise                -> 0
```

An empty `fail_on` means findings alone do not produce exit code `1`.

## 10. Non-Pipeline Features

Parallel execution, persistent cache, incremental audit state, remote service execution, and automatic remediation are not part of the current pipeline.

---
# End of Document
