# UAAF Finding Taxonomy
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-MTH-003
**Version:** 1.0
**Status:** Maintained
**Classification:** Methodology
**Owner:** Architecture

---

## 1. Purpose

Define the common interpretation of canonical UAAF findings.

## 2. Canonical Finding Shape

Every finding contains:

```text
code
severity
path
message
details
```

## 3. Severities

| Severity | Interpretation |
|---|---|
| `critical` | highest-impact review signal, including possible serious security/integrity risk |
| `error` | defect/rule violation normally requiring correction |
| `warning` | potential problem, maintainability issue, or policy concern |
| `info` | informational observation |

Severity does not itself fail the CLI unless selected through `fail_on`.

## 4. Finding Codes

Codes are plugin/domain-specific stable identifiers.

Examples currently documented include:

```text
ARCH-...
DOC-...
TEST-...
CONFIG-...
AI-...
```

A code identifies rule semantics; it is not a source location.

## 5. Path

`path` identifies the affected project artifact/element according to the emitting auditor's contract.

Canonical result validation requires a non-empty path string.

Interoperability exporters may apply stricter location rules.

## 6. Message

`message` is the human-readable explanation.

It must be non-empty and should remain deterministic for equivalent audited input when practical.

## 7. Details

`details` carries structured rule-specific evidence/metadata.

Consolidation may add provenance such as:

```text
source_plugin_id
source_audit_type
```

## 8. Findings vs Errors

A finding is an audit observation.

An `errors` entry in `AuditResult` represents execution failure information.

Do not convert execution errors into ordinary findings merely to avoid exit code `2`.

## 9. Heuristic Findings

Static heuristic findings, especially AI/security-related signals, should be treated as items for review, not proof of runtime vulnerability or exploitability.

---
# End of Document
