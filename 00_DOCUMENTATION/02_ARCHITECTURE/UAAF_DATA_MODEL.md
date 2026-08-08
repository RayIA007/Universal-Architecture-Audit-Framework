# UAAF Data Model
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-ARC-006
**Version:** 1.0
**Status:** Maintained
**Classification:** Architecture
**Owner:** Architecture

---

## 1. Purpose

Document the canonical current data structures shared by configuration, plugins, orchestration, runtime, and reporting.

## 2. AuditResult

`AuditResult` is the canonical result model.

Required serialized keys are exactly:

```text
plugin_id
plugin_version
audit_type
status
summary
metrics
findings
errors
execution
```

### Status values

```text
completed
completed_with_findings
completed_with_errors
failed
```

### Field roles

| Field | Role |
|---|---|
| `plugin_id` | canonical emitter identity |
| `plugin_version` | emitter version |
| `audit_type` | audit domain |
| `status` | canonical execution/result status |
| `summary` | structured high-level result data |
| `metrics` | structured counters/metrics |
| `findings` | ordered list of canonical findings |
| `errors` | execution error strings |
| `execution` | start/completion/duration metadata |

## 3. AuditFinding

Each serialized finding contains exactly:

```text
code
severity
path
message
details
```

Canonical severities:

```text
info
warning
error
critical
```

`details` is an extensible mapping for deterministic domain-specific evidence/metadata.

## 4. AuditExecution

Serialized execution metadata contains exactly:

```text
started_at
completed_at
duration_ms
```

`duration_ms`, when present, is a non-negative integer.

## 5. ResolvedConfig

The immutable current global configuration contains:

```text
project_path
auditors
output_formats
config_path
fail_on
exclude
output_dir
plugins_dir
framework_root
plugin_defaults
plugin_configs
```

Path fields are normalized/resolved by the configuration layer.

## 6. PluginDescriptor

The immutable plugin descriptor identifies one validated auditor and contains its runner, metadata, paths, aliases/allowed context information, and validation state.

It belongs to the registry layer and is not itself an audit result.

## 7. OrchestrationResult

One unified execution returns an `OrchestrationResult` containing:

```text
audit_results
consolidated_result
report_paths
runtime_context
exit_code
```

`audit_results` are per-plugin canonical results.

`consolidated_result` is another canonical `AuditResult`-shaped mapping emitted under the orchestrator identity.

## 8. Consolidated Finding Traceability

During consolidation the orchestrator may add source identity to finding `details`, including:

```text
source_plugin_id
source_audit_type
```

This preserves plugin provenance in the consolidated result.

## 9. JSON and SARIF

JSON reporting preserves the canonical UAAF result representation.

SARIF is a projection of canonical findings into a separate interoperability schema and is not the canonical UAAF data model.

---
# End of Document
