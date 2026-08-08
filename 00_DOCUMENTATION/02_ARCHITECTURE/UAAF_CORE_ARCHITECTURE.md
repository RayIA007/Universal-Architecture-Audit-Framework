# UAAF Core Architecture
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-ARC-001
**Version:** 2.0
**Status:** Maintained
**Classification:** Architecture
**Owner:** Architecture

---

## 1. Purpose

Define the current high-level structural architecture of UAAF.

This revision supersedes the historical component list that treated dedicated Contract, Rule, Evidence, Scoring, and Traceability engines as mandatory current components.

## 2. Canonical Architecture

```text
run.py
  |
  v
uaaf_core.cli
  |
  v
ResolvedConfig
  |
  v
UnifiedOrchestrator
  |
  +--> UAAFRegistry --> discovered / selected plugins
  |
  +--> RuntimeContext / UAAFKernel / UAAFRuntime
  |        |
  |        `--> dynamic ProcessorContract adapters
  |                 |
  |                 `--> plugin run(context)
  |
  v
ordered plugin AuditResult data
  |
  v
consolidated AuditResult
  |
  v
ReportEngine
  |
  +--> Markdown
  +--> JSON
  `--> SarifExporter --> SARIF 2.1.0
```

## 3. Core Components

Current core responsibilities are implemented by:

- `run.py` — repository entry point;
- `uaaf_core.cli` — public CLI and process-level error mapping;
- `ResolvedConfig` — immutable canonical configuration;
- `UnifiedOrchestrator` — unified execution coordinator;
- `UAAFRegistry` — processor/profile registry plus deterministic plugin registry;
- `UAAFKernel` / `UAAFRuntime` / `RuntimeContext` — runtime lifecycle and processor execution infrastructure;
- `AuditResult` — canonical auditor/consolidated result contract;
- `ReportEngine` — Markdown/JSON reporting and SARIF delegation;
- `SarifExporter` — SARIF 2.1.0 interoperability projection.

## 4. Auditor Layer

Current auditor plugins:

```text
architecture-auditor
documentation-auditor
testing-auditor
configuration-auditor
ai-systems-auditor
```

Each auditor owns its domain-specific static analysis.

The core does not implement the individual auditor rule logic.

## 5. Public Contract Boundary

Normal users interact through:

```powershell
python run.py ...
```

Plugins expose:

```python
run(context) -> dict[str, Any]
```

Returned data must satisfy the canonical audit-result contract.

## 6. Deterministic Execution

The architecture preserves deterministic ordering in discovery, selection, processor execution, result extraction, consolidation, and serialization where the implementation defines such ordering.

## 7. Configuration Boundary

The CLI and configuration loader resolve one `ResolvedConfig`.

The orchestrator projects only supported plugin-specific fields into each selected plugin's isolated context.

## 8. Reporting Boundary

Markdown and JSON represent UAAF reports derived from the canonical result.

SARIF is a stricter interoperability projection and may omit a canonical finding from SARIF `results[]` if no safe exportable artifact URI exists.

## 9. Current Limitations

The architecture currently executes selected plugins sequentially.

No current claim is made for parallel execution, persistent caching, incremental auditing, web services, SaaS operation, or automatic remediation.

## 10. Related Documents

- `UAAF_RUNTIME_ARCHITECTURE.md`
- `UAAF_LAYERED_ARCHITECTURE.md`
- `UAAF_PIPELINE_ARCHITECTURE.md`
- `UAAF_PLUGIN_ARCHITECTURE.md`
- `UAAF_DATA_MODEL.md`
- `UAAF_SECURITY_MODEL.md`
- `../../docs/architecture.md`

---
# End of Document
