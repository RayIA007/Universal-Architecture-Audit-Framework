# UAAF Evidence Standard
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-STD-004
**Version:** 1.0
**Status:** Maintained
**Classification:** Methodology Standard
**Owner:** Architecture

---

## 1. Purpose

Define what constitutes current UAAF audit evidence without relying on the historical assumption of a dedicated Evidence Engine.

## 2. Current Evidence Model

Current UAAF evidence is carried through canonical structured audit data, primarily:

- finding code;
- severity;
- path;
- message;
- finding `details`;
- plugin/audit identity;
- summary;
- metrics;
- execution metadata;
- execution errors.

## 3. Evidence Requirements

Evidence supporting a finding should be:

- attributable to the emitting auditor;
- deterministic for equivalent static input where practical;
- sufficient to explain why the rule emitted the finding;
- free from fabricated source coordinates;
- represented in structured fields when practical.

## 4. Provenance

Consolidated findings preserve source plugin/audit provenance when added by orchestration.

The canonical result remains the primary evidence carrier.

## 5. Report Representations

Markdown presents evidence for human review.

JSON preserves the canonical structured representation.

SARIF projects evidence into a third-party schema and may omit findings that cannot be assigned a safe source artifact URI.

## 6. No Fabricated Evidence

UAAF shall not invent:

- file paths;
- source lines;
- columns;
- ranges;
- fingerprints;
- scores;
- proof of vulnerability.

When evidence is unavailable, the correct behavior is to preserve the canonical finding as supported and omit unsupported interoperability fields/results.

## 7. Historical Clarification

A dedicated Evidence Engine is not a current mandatory top-level component of the unified UAAF architecture.

Future evidence subsystems must integrate with the canonical result model rather than silently replacing it.

---
# End of Document
