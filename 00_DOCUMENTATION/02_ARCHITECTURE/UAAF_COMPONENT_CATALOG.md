# UAAF Component Catalog
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-ARC-007
**Version:** 1.0
**Status:** Maintained
**Classification:** Architecture
**Owner:** Architecture

---

## 1. Purpose

Provide a concise catalog of the current components that matter to UAAF operation.

## 2. Core Components

| Component | Canonical location | Responsibility |
|---|---|---|
| Repository entry point | `run.py` | bootstraps `08_SCRIPTS`, calls CLI |
| CLI | `08_SCRIPTS/uaaf_core/cli.py` | public arguments and process-level execution |
| Global config | `08_SCRIPTS/uaaf_core/config.py` | deterministic configuration resolution |
| Unified orchestrator | `08_SCRIPTS/uaaf_core/orchestrator.py` | discovery, execution, consolidation, reports, exit code |
| Registry | `08_SCRIPTS/uaaf_core/registry.py` | processors/profiles plus dynamic plugin registry |
| Kernel | `08_SCRIPTS/uaaf_core/kernel.py` | runtime creation/coordinating core runtime infrastructure |
| Runtime | `08_SCRIPTS/uaaf_core/runtime/runtime.py` | runtime lifecycle and processor execution |
| Runtime context | `08_SCRIPTS/uaaf_core/runtime/runtime_context.py` | runtime state and processor results |
| Audit result contract | `08_SCRIPTS/uaaf_core/audit/audit_result.py` | canonical findings/results |
| Report engine | `08_SCRIPTS/uaaf_core/reporting/report_engine.py` | Markdown/JSON and format dispatch |
| SARIF exporter | `08_SCRIPTS/uaaf_core/reporting/sarif_exporter.py` | safe deterministic SARIF 2.1.0 projection |

## 3. Current Auditor Plugins

| Plugin | Location | Version |
|---|---|---:|
| Architecture Auditor | `plugins/architecture/architecture_auditor.py` | 1.6.0 |
| Documentation Auditor | `plugins/documentation/documentation_auditor.py` | 1.0.0 |
| Testing Auditor | `plugins/testing/testing_auditor.py` | 1.0.0 |
| Configuration Auditor | `plugins/configuration/configuration_auditor.py` | 1.0.0 |
| AI Systems Auditor | `plugins/ai_systems/ai_systems_auditor.py` | 1.0.0 |

## 4. CI Component

```text
.github/workflows/uaaf-ci.yml
```

Current canonical CI validates:

- Python environment;
- full pytest suite;
- CLI help;
- controlled UAAF smoke execution;
- Markdown/JSON/SARIF artifacts;
- SARIF safety properties;
- eligible GitHub Code Scanning upload.

## 5. Public Documentation

```text
README.md
docs/architecture.md
docs/cli-and-configuration.md
docs/plugins.md
docs/reporting-and-sarif.md
docs/development.md
```

## 6. Permanent Documentation

`00_DOCUMENTATION/` contains governance, architecture, methodology, and planning records.

Transient session context files are not permanent components.

## 7. Historical Components Not in the Current Mandatory Architecture

The following names may appear in historical material but are not current mandatory top-level components:

- Contract Engine;
- Rule Engine;
- Evidence Engine;
- Scoring Engine;
- Traceability Engine;
- Patch Engine.

Existing lower-level modules may remain for compatibility or runtime infrastructure, but current architecture is defined by implemented responsibilities, not historical labels.

---
# End of Document
