# UAAF Document Hierarchy
**Universal Architecture Audit Framework v1.0**

**Document ID:** UAAF-GOV-001  
**Version:** 1.0  
**Status:** Approved  
**Classification:** Governance Standard

---

# 1. Purpose

This document defines the official documentation hierarchy of the Universal Architecture Audit Framework (UAAF).

Its purpose is to establish the authority, responsibility and dependency rules for every official document within the framework.

---

# 2. Documentation Principles

The UAAF documentation shall follow these principles:

- One document, one responsibility.
- No duplicated information.
- Higher-level documents govern lower-level documents.
- Lower-level documents shall never contradict higher-level documents.
- Every document shall have an identifiable owner and purpose.

---

# 3. Authority Levels

| Level | Document Type | Purpose |
|--------|---------------|---------|
| 0 | Constitution | Defines the permanent identity and principles of UAAF. |
| 1 | Governance | Defines governance rules and documentation policies. |
| 2 | Architecture | Defines the structure and organization of the framework. |
| 3 | Standards | Defines mandatory engineering rules. |
| 4 | Specifications | Defines functional and technical contracts. |
| 5 | Methodologies | Defines repeatable audit processes. |
| 6 | Schemas | Defines data structures and validation models. |
| 7 | Profiles | Defines project-specific audit configurations. |
| 8 | Rule Packs | Defines auditable rules. |
| 9 | Templates | Defines reusable document formats. |

---

# 4. Dependency Rules

Documents may only depend on documents at the same level or higher.

Dependencies shall never create circular references.

---

# 5. Conflict Resolution

When two documents conflict, the document with the highest authority prevails.

If documents share the same authority level, the conflict shall be resolved through governance review.

---

# 6. Document Ownership

Every official document shall define:

- Document ID
- Version
- Status
- Classification
- Owner

No anonymous documents are permitted.

---

# 7. Version Control

Every revision shall:

- Preserve document history.
- Maintain version numbering.
- Record architectural changes.
- Preserve backward traceability.

---

# 8. Traceability

Each document shall explicitly reference its governing documents.

Traceability shall be maintained throughout the entire framework.

---

# 9. Document Lifecycle

Every official document shall follow the same lifecycle:

Draft

↓

Review

↓

Approved

↓

Implemented (if applicable)

↓

Maintained

↓

Deprecated (optional)

↓

Archived (optional)

---

# 10. Naming Convention

Official documents shall use the following identifier format:

UAAF-[TYPE]-[NUMBER]

Examples:

- UAAF-CON-001
- UAAF-GOV-001
- UAAF-ARC-001
- UAAF-STD-001
- UAAF-SPEC-001
- UAAF-MTH-001
- UAAF-CTR-001
- UAAF-RUL-001

---

# 11. Documentation Responsibility Matrix

| Document Type | Responsible For |
|---------------|-----------------|
| Constitution | Identity and principles |
| Governance | Governance and hierarchy |
| Architecture | Structural design |
| Standards | Engineering rules |
| Specifications | Functional contracts |
| Methodologies | Audit procedures |
| Schemas | Data validation |
| Profiles | Audit configuration |
| Rule Packs | Audit criteria |
| Templates | Reusable formats |

---

# 12. Compliance

Every document within UAAF shall comply with this hierarchy.

Non-compliant documentation shall be considered invalid until corrected.

---

# End of Document