# UAAF Architecture Standard
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-STD-003
**Version:** 1.0
**Status:** Maintained
**Classification:** Architecture Standard
**Owner:** Architecture

---

## 1. Purpose

Define mandatory rules for describing and evolving the current UAAF architecture.

## 2. Governing Documents

- `../01_GOVERNANCE/UAAF_CORE_CONSTITUTION.md`
- `../01_GOVERNANCE/UAAF_DOCUMENT_HIERARCHY.md`
- `../01_GOVERNANCE/UAAF_ENGINEERING_STANDARD.md`

## 3. Current Architectural Style

UAAF is currently a Python, plugin-oriented, deterministic audit framework executed through one repository CLI.

The canonical current flow is:

```text
run.py
  -> uaaf_core.cli
  -> ResolvedConfig
  -> UnifiedOrchestrator
  -> UAAFRegistry + runtime
  -> selected auditor plugins
  -> AuditResult-compatible results
  -> consolidated AuditResult
  -> ReportEngine
  -> Markdown / JSON / optional SARIF 2.1.0
```

## 4. Architectural Responsibilities

The architecture shall keep these responsibilities separated:

- entry point and CLI parsing;
- configuration resolution;
- plugin discovery/selection;
- runtime lifecycle;
- auditor-specific analysis;
- canonical result validation/consolidation;
- reporting/interoperability;
- exit-code policy.

## 5. Dependency Direction

User-facing layers may depend inward on core contracts and runtime services.

Auditor plugins depend on public/canonical contracts but the core shall not contain auditor-specific rule logic.

Reporting consumes canonical results and shall not perform auditor analysis.

The registry discovers/selects plugins but shall not execute them or generate reports.

## 6. Current Runtime Boundary

The current unified orchestrator adapts discovered auditor plugins into runtime processor contracts, executes them sequentially through the existing kernel/runtime pipeline, extracts canonical results, consolidates them, and writes reports.

Dedicated historical "engines" are not mandatory architecture components merely because older documents named them.

## 7. Extension Rules

New auditors should be added as plugins compatible with the registry and canonical result contract.

New output formats should consume canonical results and remain separate from auditor analysis.

New CLI/configuration behavior must be reflected through `ResolvedConfig` and tests.

## 8. Unsupported-as-Current Boundaries

The current architecture does not claim:

- parallel/multiprocess auditor execution;
- persistent AST cache;
- incremental audit mode;
- dashboard/web UI;
- REST API;
- Cloud/SaaS execution;
- automatic remediation;
- a Patch Engine as a current UAAF component.

## 9. Documentation Rule

`docs/architecture.md` is the public operational description.

The documents in this directory are the permanent architectural record and must remain consistent with the implementation.

---
# End of Document
