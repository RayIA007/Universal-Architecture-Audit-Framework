# UAAF Document Hierarchy
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-GOV-001
**Version:** 1.1
**Status:** Maintained
**Classification:** Governance Standard
**Owner:** Architecture

---

## 1. Purpose

This document defines the official documentation hierarchy, ownership requirements, conflict rules, and lifecycle for UAAF documents.

## 2. Documentation Principles

- One document, one primary responsibility.
- No unnecessary duplicated normative text.
- Higher-authority documents govern lower-authority documents.
- Lower-authority documents shall not contradict higher-authority documents.
- Every official document shall have an identifiable owner and purpose.
- Current-state documentation shall clearly distinguish implemented behavior from roadmap or historical material.

## 3. Authority Levels

| Level | Document Type | Purpose |
|---:|---|---|
| 0 | Constitution | Permanent identity and principles |
| 1 | Governance | Governance rules and documentation policy |
| 2 | Architecture | Structural organization and runtime relationships |
| 3 | Standards | Mandatory engineering/documentation rules |
| 4 | Specifications | Functional and technical contracts |
| 5 | Methodologies | Repeatable audit processes |
| 6 | Schemas | Data validation structures |
| 7 | Profiles | Project-specific audit configuration |
| 8 | Rule Packs | Auditable criteria |
| 9 | Templates | Reusable formats |
| 10 | Planning / Roadmap | Planned work, acceptance criteria, and historical milestones |
| 11 | Public Guides | User-facing operational documentation |

Planning and public guides cannot override contracts, standards, architecture, governance, or the Constitution.

## 4. Dependency Rules

Documents may depend on documents at the same level or a higher-authority level.

References should point to the authoritative source instead of duplicating large blocks of normative content.

Circular normative dependencies are prohibited.

## 5. Conflict Resolution

When two documents conflict:

1. the higher-authority document prevails;
2. if both have the same authority, architectural/governance review resolves the conflict;
3. if descriptive documentation conflicts with implemented behavior, the discrepancy must be corrected before the documentation can be treated as current-state documentation.

## 6. Document Ownership

Every official document shall define:

- Document ID;
- Version;
- Status;
- Classification;
- Owner.

No anonymous official documents are permitted.

## 7. Version Control

Every revision shall:

- increment the document version when normative or structural meaning changes;
- preserve history through Git;
- record major architectural changes in `CHANGELOG.md`;
- preserve backward traceability to superseded decisions where useful.

## 8. Traceability

Each official document shall identify its governing context or reference the documents that govern it.

Code-level behavior should be referenced by canonical module or contract names when implementation detail is necessary.

## 9. Document Lifecycle

```text
Draft
  ↓
Review
  ↓
Approved
  ↓
Implemented (when applicable)
  ↓
Maintained
  ↓
Deprecated (optional)
  ↓
Archived (optional)
```

## 10. Naming Convention

Official document identifiers use:

```text
UAAF-[TYPE]-[NUMBER]
```

Current type families include:

```text
UAAF-CONSTITUTION-###
UAAF-GOV-###
UAAF-ARC-###
UAAF-STD-###
UAAF-SPEC-###
UAAF-MTH-###
UAAF-PLAN-###
```

Existing IDs are preserved even when later conventions become more concise.

## 11. Current Permanent Documentation Responsibilities

| Area | Directory | Responsibility |
|---|---|---|
| Governance | `00_DOCUMENTATION/01_GOVERNANCE/` | Principles, hierarchy, governance, language, engineering rules |
| Architecture | `00_DOCUMENTATION/02_ARCHITECTURE/` | Current structural architecture and implementation boundaries |
| Methodology | `00_DOCUMENTATION/03_METHODOLOGY/` | Audit, findings, evidence, traceability, scoring policy, reporting |
| Planning | `00_DOCUMENTATION/04_PLANNING/` | Completed milestones, current acceptance baseline, future roadmap |
| Public guides | `README.md`, `docs/` | User-facing operation and examples |
| History | `CHANGELOG.md`, Git history | Milestones and significant changes |

Transient session files are not permanent documentation and shall not be required to understand or operate UAAF.

## 12. Compliance

A document that lacks required metadata, presents historical design as current implementation, or contradicts a higher-authority document shall be corrected before being considered current.

---
# End of Document
