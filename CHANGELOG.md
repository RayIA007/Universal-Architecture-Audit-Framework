# UAAF Changelog

This file records significant permanent UAAF milestones. Detailed line-level history remains in Git.

## 2026-08-08 — Phase 3 closed

### Documentation consolidation preparation

- Phase 3.6 public documentation completed.
- Public documentation commit: `914ece3`.
- Phase 3.6 closure/context commit: `b597d6b`.
- Final maintained test baseline: `820 passed`.
- Final closure workflow observed as UAAF CI #9: success.
- Permanent documentation consolidation authorized before the next functional phase.
- Transient session context/plan files designated for retirement after their permanent information is migrated.

### Phase 3.6 — Public Documentation

Added/established:

- `README.md`;
- `docs/architecture.md`;
- `docs/cli-and-configuration.md`;
- `docs/plugins.md`;
- `docs/reporting-and-sarif.md`;
- `docs/development.md`.

Public documentation explicitly describes implemented behavior and does not advertise roadmap items as current features.

## 2026-08 — Phase 3.5 — SARIF

- Added deterministic SARIF 2.1.0 export.
- Added safe artifact-URI handling.
- Preserved canonical findings when SARIF cannot safely export a location.
- Validated GitHub Code Scanning upload remotely.
- Final SARIF validation included UAAF CI #6 on commit `62424728d1609233d933207e1a58747153f304bc`.

## 2026-08 — Phase 3.4 — CI/CD

- Added/validated canonical GitHub Actions workflow.
- Full tests, CLI help, controlled smoke execution, report verification, and eligible Code Scanning integration established.
- Remote validation included workflow run #4 on commit `fb3f72b`.

## 2026-08 — Phase 3.3 — Global Configuration

- Added immutable `ResolvedConfig`.
- Added JSON/TOML/YAML/YML loading.
- Added TOML `[tool.uaaf]`.
- Established precedence:

```text
framework defaults < configuration file < explicit CLI
```

- Established stable exclusion merging and plugin-specific configuration validation.

## 2026-08 — Phase 3.2 — Dynamic Plugin Registry

- Consolidated `UAAFRegistry` as the canonical dynamic auditor registry.
- Added deterministic discovery, registration, aliases, selection, duplicate detection, and plugin metadata validation.
- Preserved existing processor/profile registry responsibilities.

## 2026-08 — Phase 3.1 — Unified Orchestrator / CLI

- Added `UnifiedOrchestrator`.
- Added unified public CLI.
- Added deterministic selected-plugin execution and result consolidation.
- Established exit codes `0`, `1`, and `2`.
- Integrated five auditor plugins into one execution path.

## Phase 2 — Auditor and Reporting Expansion

- Added/established Report Engine for Markdown and JSON.
- Added Documentation Auditor.
- Added Testing Auditor.
- Added Configuration Auditor.
- Added AI Systems Auditor.
- Integrated all auditors with the canonical `AuditResult`.
- Added advanced Architecture Auditor semantic features.

## Phase 1 — Architecture Auditor MVP

- Established Architecture Auditor contract/configuration/discovery/import/rule/robustness/runtime integration suites.
- Architecture Auditor reached version `1.6.0`.
- Recorded Architecture Auditor-related baseline: `232` tests.

## Current roadmap boundary

The completed principal roadmap is Phases 1–3.

Future performance, multi-language, Cloud/SaaS, and remediation concepts remain unimplemented roadmap items.

Patch Engine / automatic patch generation is not a current UAAF component and is reserved for separate architectural review.
