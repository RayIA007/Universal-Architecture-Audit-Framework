# UAAF Security Model
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-ARC-009
**Version:** 1.0
**Status:** Maintained
**Classification:** Architecture and Security
**Owner:** Architecture

---

## 1. Purpose

Document the current security boundaries and conservative handling rules implemented or required by UAAF.

## 2. Trust Boundaries

### Audited project

Project files are audit input and should be treated as untrusted content.

Auditors primarily perform static inspection; documentation must not imply that findings prove exploitability.

### Auditor plugins

Discovered plugins are imported and executed as Python code.

Therefore plugin code is trusted executable code, not sandboxed input. A custom `--plugins-dir` must only reference trusted plugin code.

### Configuration

Configuration can influence audited paths, plugin selection, output location, and plugin-specific settings.

Invalid or conflicting configuration is rejected by the configuration layer.

## 3. Sensitive Configuration

`ResolvedConfig.to_dict()` supports redacted diagnostic snapshots.

Sensitive-key matching includes concepts such as API keys, credentials, passwords, secrets, and tokens.

Documentation and logs should use redacted snapshots when exposing configuration diagnostics.

## 4. Finding Safety

A finding is a static audit signal.

AI Systems and Configuration findings that detect secret-like content or risky patterns must not be interpreted automatically as proof of a real credential or production vulnerability.

## 5. SARIF Path Safety

The SARIF exporter:

- normalizes safe artifact URIs to project-relative POSIX paths;
- avoids paths that escape the audited project;
- avoids unsafe absolute Windows/UNC forms;
- redacts project-root text in messages where required;
- omits a SARIF result when no safe exportable artifact URI exists;
- preserves the canonical finding in Markdown/JSON rather than inventing a location.

## 6. CI Security

The canonical GitHub Actions workflow uses read-only repository contents permission and grants job-level `security-events: write` only for Code Scanning upload.

SARIF upload is skipped for fork-origin pull requests.

The workflow does not rely on repository secrets for SARIF upload.

## 7. Output Boundary

Generated reports can contain project paths, finding messages, metrics, or source-derived data depending on format and plugin.

Users should review reports before publishing them outside the intended environment.

## 8. No Current Remote Service Boundary

Current UAAF is executed from source as a local/CI Python framework.

There is no current UAAF REST API, SaaS control plane, or dashboard security model.

## 9. Automatic Remediation Boundary

UAAF does not currently perform automatic code remediation or patch application.

Any Patch Engine/auto-remediation capability is outside the current security model and requires a separate architecture/security review.

---
# End of Document
