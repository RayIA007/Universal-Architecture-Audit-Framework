# UAAF Layered Architecture
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-ARC-003
**Version:** 1.0
**Status:** Maintained
**Classification:** Architecture
**Owner:** Architecture

---

## 1. Purpose

Describe the current logical layers of UAAF and their permitted responsibilities.

## 2. Layers

### Layer A — Entry and Public Interface

Components:

- `run.py`
- `uaaf_core.cli`

Responsibilities:

- expose public CLI;
- parse and normalize public options;
- invoke one unified execution;
- map expected top-level failures to process semantics.

### Layer B — Configuration

Component:

- `uaaf_core.config`
- `ResolvedConfig`

Responsibilities:

- load supported JSON/TOML/YAML configuration;
- apply deterministic precedence;
- normalize paths, formats, severities, exclusions, and plugin settings;
- redact sensitive diagnostic snapshots.

### Layer C — Orchestration and Registry

Components:

- `UnifiedOrchestrator`
- `UAAFRegistry`

Responsibilities:

- discover and select plugins;
- validate plugin descriptors/configuration;
- build isolated plugin contexts;
- coordinate runtime execution;
- consolidate results;
- decide exit code.

### Layer D — Runtime and Contracts

Components include:

- `UAAFKernel`
- `UAAFRuntime`
- `RuntimeContext`
- `RuntimePipeline`
- `ProcessorContract`
- `AuditProfile`

Responsibilities:

- execute selected processors in profile order;
- preserve runtime lifecycle/state;
- store normalized processor outputs.

### Layer E — Auditor Plugins

Current packages:

- `plugins/architecture`
- `plugins/documentation`
- `plugins/testing`
- `plugins/configuration`
- `plugins/ai_systems`

Responsibilities:

- domain-specific static analysis;
- return canonical result mappings.

### Layer F — Canonical Audit Data

Primary contract:

- `AuditResult`
- `AuditFinding`
- `AuditExecution`

Responsibilities:

- normalize plugin identity, status, findings, metrics, errors, and execution metadata.

### Layer G — Reporting and Interoperability

Components:

- `ReportEngine`
- `SarifExporter`

Responsibilities:

- Markdown rendering;
- JSON serialization;
- SARIF 2.1.0 projection;
- report naming/writing.

## 3. Dependency Rules

- Auditor analysis shall not be implemented in CLI/reporting.
- Reporting shall consume canonical results rather than call auditors.
- Registry shall not generate reports.
- Plugin configuration shall not override reserved framework context fields.
- Public CLI behavior shall be resolved into `ResolvedConfig` before canonical execution.

## 4. Cross-Cutting Concerns

Determinism, path safety, error semantics, testing, and documentation apply across layers.

---
# End of Document
