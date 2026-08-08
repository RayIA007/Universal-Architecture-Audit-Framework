# UAAF Traceability Standard
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-STD-005
**Version:** 1.0
**Status:** Maintained
**Classification:** Methodology Standard
**Owner:** Architecture

---

## 1. Purpose

Define traceability requirements across audit configuration, plugin execution, findings, consolidated results, reports, and CI.

## 2. Minimum Finding Traceability

A canonical finding is traceable through:

- emitting plugin identity;
- audit type;
- finding code;
- project-relative/normalized path information as provided by the auditor;
- message;
- structured details.

## 3. Execution Traceability

One audit execution is traceable through:

- resolved project path/configuration;
- selected auditor identities;
- per-plugin statuses;
- execution timestamps/durations when present;
- execution errors;
- consolidated result;
- generated report paths.

## 4. Consolidated Provenance

The orchestrator preserves source plugin/audit provenance in consolidated finding details where needed.

## 5. Configuration Traceability

`ResolvedConfig` is the canonical interpreted configuration for one unified execution.

Diagnostics should use redacted snapshots when sensitive keys may be present.

## 6. Report Traceability

Markdown and JSON are generated from canonical result data.

SARIF is generated from the same canonical finding set under stricter interoperability/location rules.

A SARIF omission caused by an unsafe/unavailable source URI must not delete the canonical UAAF finding.

## 7. CI Traceability

Git commits and GitHub Actions runs provide repository-level traceability for validated milestones.

Permanent milestone history belongs in `CHANGELOG.md` and planning documentation rather than transient session notes.

## 8. Historical Clarification

A dedicated Traceability Engine is not required to satisfy the current traceability contract.

Traceability is an end-to-end property of canonical data, deterministic orchestration, reports, tests, and version control.

---
# End of Document
