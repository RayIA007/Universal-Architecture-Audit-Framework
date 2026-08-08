# UAAF Language Standard
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-STD-001
**Version:** 1.0
**Status:** Maintained
**Classification:** Documentation and Engineering Standard
**Owner:** Architecture

---

## 1. Purpose

Define the language and terminology rules used by official UAAF source documentation.

## 2. Governing Documents

- `UAAF_CORE_CONSTITUTION.md`
- `UAAF_DOCUMENT_HIERARCHY.md`

## 3. Normative Repository Language

Normative UAAF documentation, source identifiers, public CLI option names, finding codes, and technical contract names are written in English unless an existing public contract requires otherwise.

Explanatory material outside the repository may be translated without changing the canonical identifiers.

## 4. Canonical Terms

Use current implementation names exactly:

- `ResolvedConfig`
- `UnifiedOrchestrator`
- `UAAFRegistry`
- `RuntimeContext`
- `AuditResult`
- `AuditFinding`
- `ReportEngine`
- `SarifExporter`
- `run(context) -> dict[str, Any]`

Do not replace canonical identifiers with translated aliases inside technical contracts.

## 5. Status Language

Use these distinctions consistently:

- **implemented/current**: present in code and validated;
- **supported**: accepted by current public contract;
- **validated**: demonstrated in the documented environment/workflow;
- **historical**: previously planned or implemented but not the current canonical description;
- **planned/future**: roadmap only, not available behavior;
- **deprecated**: intentionally retained for compatibility but not recommended.

## 6. Prohibited Documentation Language

Documentation shall not:

- describe planned features as implemented;
- imply validation on platforms or versions not actually validated;
- claim installation/distribution paths not provided by the repository;
- convert heuristic audit findings into proof of a vulnerability or defect;
- call SARIF the canonical UAAF data model.

## 7. Paths and Commands

Repository paths use code formatting.

Examples for the currently validated local environment may use PowerShell syntax. Paths embedded in canonical findings/reports should follow the implementation's normalized path rules.

## 8. Examples

Examples must use real public options and current plugin selectors.

Prefer:

```powershell
python run.py --project-path . --auditors architecture,testing
```

Do not publish hypothetical CLI flags as if they exist.

---
# End of Document
