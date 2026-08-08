# UAAF Scoring Methodology
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-MTH-002
**Version:** 1.0
**Status:** Maintained
**Classification:** Methodology
**Owner:** Architecture

---

## 1. Purpose

Clarify the status of scoring in the current UAAF implementation and prevent historical scoring concepts from being presented as current capability.

## 2. Current State

The current unified UAAF CLI does **not** define or publish a canonical global numeric audit score.

Current decision semantics are based on:

- canonical finding severities;
- plugin execution status/errors;
- optional `fail_on` severity configuration;
- exit codes `0`, `1`, and `2`.

## 3. Severity Is Not a Numeric Score

Canonical severities are:

```text
info
warning
error
critical
```

These values classify finding impact/attention level.

They are not converted by the current unified CLI into a universal numeric grade.

## 4. Quality-Gate Semantics

Configured `fail_on` severities control process status:

```text
matching configured severity -> exit code 1
execution failure             -> exit code 2
otherwise                     -> exit code 0
```

This is a gate, not a scoring algorithm.

## 5. Historical Scoring References

Historical architecture/planning may reference a Scoring Engine, score artifacts, or score calculation stage.

Those references are not part of the current canonical unified architecture unless a future implementation explicitly introduces and validates them.

## 6. Future Scoring Requirements

If scoring is introduced later, it must define:

- mathematical model;
- input findings/metrics;
- weighting;
- normalization;
- missing-data behavior;
- reproducibility rules;
- versioning;
- tests;
- compatibility with existing severity/exit semantics.

Until then, no document shall imply that UAAF produces a universal score.

---
# End of Document
