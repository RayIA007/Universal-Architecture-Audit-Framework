# UAAF Acceptance Criteria
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-PLAN-003
**Version:** 1.0
**Status:** Maintained
**Classification:** Planning and Acceptance
**Owner:** Architecture

---

## 1. Purpose

Define acceptance criteria for the current completed Phase 3 UAAF baseline and for future milestone closure.

## 2. Current Product Baseline

The current baseline is accepted when all of the following remain true:

- repository entry point runs through `python run.py`;
- public CLI exposes only documented options;
- global configuration resolves deterministically;
- five current plugins are discoverable;
- plugin selection is deterministic;
- plugins return canonical audit-result data;
- Markdown and JSON reporting work;
- SARIF 2.1.0 remains optional and safe;
- exit codes `0`, `1`, and `2` retain documented semantics;
- full test suite passes;
- canonical CI succeeds.

## 3. Current Documentation Baseline

Acceptance requires:

- `README.md` describes implemented behavior;
- `docs/` explains architecture, CLI/configuration, plugins, reporting/SARIF, development/CI;
- permanent `00_DOCUMENTATION/` does not present historical architecture as current;
- future roadmap items are visibly marked as future;
- no permanent documentation depends on transient session files.

## 4. Documentation Transition Acceptance

The post-Phase-3 transition is accepted when:

- permanent session information is migrated;
- empty permanent documents relevant to the current system are completed;
- historical architecture is corrected or explicitly classified;
- the two transient session context/plan files are removed;
- no broken references to those files remain;
- `git diff --check` is clean;
- full tests pass;
- focused commit is pushed;
- remote CI succeeds;
- working tree is clean.

## 5. Functional Change Acceptance

A future functional change additionally requires:

- implementation-specific tests;
- updated permanent architecture/standards;
- updated public documentation if behavior is user-visible;
- compatibility decision for changed public contracts.

## 6. Non-Acceptance Conditions

A milestone is not accepted if documentation:

- invents features;
- claims unvalidated platforms;
- claims a packaging/install method not present;
- presents roadmap functionality as current;
- fabricates evidence or source locations;
- hides execution errors as ordinary findings.

---
# End of Document
