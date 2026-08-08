# UAAF Engineering Standard
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-STD-002
**Version:** 1.0
**Status:** Maintained
**Classification:** Engineering Standard
**Owner:** Architecture

---

## 1. Purpose

Define engineering rules that preserve UAAF correctness, determinism, compatibility, and maintainability.

## 2. Governing Documents

- `UAAF_CORE_CONSTITUTION.md`
- `UAAF_DOCUMENT_HIERARCHY.md`

## 3. Contract Preservation

Current public contracts shall not be changed accidentally.

Key contracts include:

- repository entry point: `python run.py`;
- plugin runner: `run(context) -> dict[str, Any]`;
- canonical result validation through `AuditResult`;
- global configuration through `ResolvedConfig`;
- deterministic discovery/selection through `UAAFRegistry`;
- exit codes `0`, `1`, and `2`;
- Markdown/JSON reporting and optional SARIF 2.1.0.

## 4. Determinism

Implementation changes should preserve stable behavior for equivalent inputs, including:

- plugin discovery/selection order;
- normalized configuration;
- exclusion merging;
- finding normalization/order where defined;
- report serialization;
- SARIF rule/result construction.

Timestamps and measured durations are allowed to vary.

## 5. Error Handling

Expected invalid configuration, plugin discovery problems, and runtime/plugin execution failures shall be represented explicitly.

Execution failure semantics take precedence over finding-based quality gates.

## 6. Configuration

Configuration precedence is:

```text
framework defaults < configuration file < explicit CLI values
```

Exclusions from the configuration file and explicit CLI are merged in stable first-seen order.

Sensitive configuration snapshots shall use the implementation's redaction behavior.

## 7. Plugin Isolation

Plugin-specific configuration must be projected only into supported fields.

Reserved framework fields such as `project_path` and `audit_type` shall not be overridden by plugin configuration.

## 8. Reporting and Paths

Canonical findings are preserved in UAAF data even when an interoperability format cannot safely export a source location.

SARIF shall not invent locations, columns, ranges, or fingerprints.

Unsafe/absolute project-root text shall not be exposed through SARIF when the exporter can safely redact or omit it.

## 9. Testing

Changes require the narrowest relevant tests plus the full suite before milestone closure.

The maintained full-suite baseline at the close of Phase 3 is:

```text
820 passed
```

## 10. Dependencies

New external dependencies require explicit technical justification.

Current CI intentionally pins the dependencies documented in `README.md` and `docs/development.md`.

## 11. Documentation

A functional change is not complete until permanent/current documentation is updated.

Historical or aspirational architecture shall not be copied into current-state documents without verification against code/tests.

---
# End of Document
