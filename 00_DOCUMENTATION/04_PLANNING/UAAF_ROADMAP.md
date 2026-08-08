# UAAF Roadmap
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-PLAN-004
**Version:** 1.0
**Status:** Maintained
**Classification:** Planning
**Owner:** Architecture

---

## 1. Purpose

Provide the permanent roadmap after completion of the initial UAAF consolidation.

Roadmap entries are planning intentions, not implemented features.

## 2. Completed Roadmap

| Phase | Scope | Status |
|---|---|---|
| 1 | Architecture Auditor MVP | Completed |
| 2 | Reporting + additional auditors + semantic architecture features | Completed |
| 3.1 | Unified Orchestrator / CLI | Completed |
| 3.2 | Dynamic Plugin Registry | Completed |
| 3.3 | Global Configuration | Completed |
| 3.4 | GitHub Actions CI/CD | Completed / remotely validated |
| 3.5 | SARIF 2.1.0 / Code Scanning | Completed / remotely validated |
| 3.6 | Public Documentation | Completed / remotely validated |

## 3. Administrative Transition After Phase 3

Before a new functional phase:

- consolidate permanent documentation;
- retire session context/plan files;
- preserve the existing `00_DOCUMENTATION/` structure;
- validate no functional code changes were introduced.

## 4. Planned Future Functional Areas

| Planned phase | Objective | Current status |
|---|---|---|
| Phase 4 — Performance | evaluate parallelization, AST caching, incremental audits | Not implemented |
| Phase 5 — Multi-language | evaluate TypeScript/JavaScript auditing | Not implemented |
| Phase 6 — Cloud/SaaS | evaluate remote audit/history/trends | Not implemented |
| Phase 7 — Auto-remediation concept | evaluate remediation workflow outside current UAAF core | Not implemented / architecture review required |

No date or compatibility commitment is implied by this table.

## 5. Patch Engine Decision

Patch generation is not a current UAAF capability.

The next architectural review must separate Patch Engine / automatic patch-generation concerns from UAAF and treat them as a dedicated project/architecture unless a later governance decision explicitly changes that boundary.

Until that review is completed, no Patch Engine component shall be added to current UAAF architecture documentation.

## 6. Future Phase Entry Criteria

A new functional phase should start only when:

- the documentation transition is closed;
- repository state is clean;
- current tests/CI are green;
- scope and acceptance criteria are defined;
- roadmap behavior is not advertised as current before implementation.

---
# End of Document
