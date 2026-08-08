# UAAF Governance Model
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-GOV-002
**Version:** 1.0
**Status:** Maintained
**Classification:** Governance
**Owner:** Architecture

---

## 1. Purpose

Define how UAAF architectural, implementation, documentation, and roadmap changes are controlled.

## 2. Governing Documents

This document is governed by:

- `UAAF_CORE_CONSTITUTION.md`;
- `UAAF_DOCUMENT_HIERARCHY.md`.

## 3. Change Classes

### 3.1 Documentation-only change

A change is documentation-only when it does not alter runtime behavior, public CLI behavior, plugin execution, report serialization, configuration semantics, tests, or CI behavior.

Documentation-only changes still require:

- factual verification against the repository;
- `git diff --check`;
- test-suite validation when the changed documentation is part of a milestone closure;
- focused staging and commit review.

### 3.2 Backward-compatible implementation change

Requires:

- tests for the changed behavior;
- preservation of public contracts unless explicitly versioned;
- permanent/public documentation updates;
- CI validation.

### 3.3 Breaking change

Requires architectural review, an explicit compatibility decision, updated contracts, tests, documentation, and migration guidance.

## 4. Sources of Truth

For permanent governance and architectural intent, higher-authority documents govern.

For statements about what the current executable repository actually does, the implementation and its tests are the factual baseline. If descriptive documents disagree with implementation, the documents must be corrected rather than inventing behavior.

Public documentation must never advertise a roadmap item as available.

## 5. Current Release Validation Baseline

At the close of the completed Phase 3 roadmap:

- complete local test suite: `820 passed`;
- validated platform: Windows;
- validated Python: `3.14.6`;
- validated pytest: `9.1.1`;
- five auditor plugins;
- GitHub Actions validated on `main`;
- SARIF 2.1.0 and GitHub Code Scanning upload validated.

Timing values for individual test runs are historical evidence, not normative requirements.

## 6. Required Review for Documentation Consolidation

When transient/session documentation is retired:

1. identify permanent information;
2. move current architecture into `00_DOCUMENTATION/02_ARCHITECTURE/`;
3. move audit/report/testing rules into `00_DOCUMENTATION/03_METHODOLOGY/`;
4. move roadmap/history into `00_DOCUMENTATION/04_PLANNING/` and `CHANGELOG.md`;
5. remove transient files only after the information is preserved;
6. verify that no permanent document depends on the removed files.

## 7. Repository Structure Policy

`00_DOCUMENTATION/` remains in its established location and four-directory structure unless a demonstrated technical need requires a change.

Cosmetic reorganization alone is not sufficient justification.

## 8. Roadmap Governance

Future roadmap entries are planning artifacts only.

They become current capability only after:

- implementation;
- tests;
- permanent documentation;
- public documentation when user-facing;
- local validation;
- remote CI validation where applicable.

## 9. Patch Engine Boundary

Patch generation and automatic remediation are not current UAAF runtime capabilities.

Any future Patch Engine or automated patch-generation system is to be evaluated as a separate project/architecture rather than silently becoming a mandatory UAAF component.

---
# End of Document
