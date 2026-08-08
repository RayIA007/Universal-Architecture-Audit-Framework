# UAAF Report Standard
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-STD-006
**Version:** 1.0
**Status:** Maintained
**Classification:** Reporting Standard
**Owner:** Architecture

---

## 1. Purpose

Define the current report formats and representation rules for UAAF.

## 2. Canonical Input

`ReportEngine` consumes validated canonical `AuditResult` data.

Reporting must not perform auditor-specific analysis or change finding meaning.

## 3. Supported Formats

```text
markdown
json
sarif
```

Default formats:

```text
markdown,json
```

SARIF is opt-in.

## 4. Markdown

Markdown is the human-readable UAAF report.

It represents audit identity/status, summary, metrics, findings, execution metadata, and errors when present.

## 5. JSON

JSON is the machine-readable representation of the canonical UAAF result.

When another system needs complete canonical UAAF data, JSON is preferred over SARIF.

## 6. SARIF 2.1.0

SARIF is an interoperability projection.

Current exporter properties include:

- SARIF `2.1.0`;
- official SARIF 2.1.0 Errata 01 schema URI;
- deterministic UAAF rule/result construction;
- severity mapping;
- safe project-relative POSIX artifact URIs;
- conservative source-location handling.

## 7. Severity Mapping to SARIF

| UAAF | SARIF |
|---|---|
| `critical` | `error` |
| `error` | `error` |
| `warning` | `warning` |
| `info` | `note` |

## 8. Location Rule

A canonical finding is exported as a SARIF result only when the exporter can produce a safe exportable artifact URI.

If not:

```text
canonical finding -> preserved
Markdown/JSON     -> preserved
SARIF result      -> omitted
```

No source location shall be invented.

## 9. Output Directory

Default output location:

```text
<UAAF_ROOT>/07_OUTPUTS
```

Users may override it with `--output-dir`.

## 10. Exit Codes

Report content does not independently determine process exit semantics.

Exit code is determined by execution failure and configured `fail_on` finding severities.

## 11. GitHub Code Scanning

The canonical CI workflow validates SARIF before eligible upload through `github/codeql-action/upload-sarif@v4`.

Detailed public usage is documented in `../../docs/reporting-and-sarif.md`.

---
# End of Document
