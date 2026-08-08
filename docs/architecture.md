# UAAF Architecture

This document describes the architecture implemented by the current Universal Architecture Audit Framework (UAAF) codebase.

It intentionally does not treat historical design documents or roadmap concepts as current runtime components.

## What the architecture is

UAAF is a plugin-oriented audit pipeline with a single public CLI. The core framework is responsible for configuration, plugin discovery/selection, execution, result consolidation, report generation, and process exit semantics. Individual auditors are responsible for domain-specific static analysis.

## Canonical flow

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
  +------------------+
  |                  |
  v                  v
UAAFRegistry      RuntimeContext
  |
  v
Selected plugins
  |
  v
run(context) -> dict[str, Any]
  |
  v
AuditResult-compatible data
  |
  v
Consolidated AuditResult
  |
  v
ReportEngine
  |
  +--> Markdown
  +--> JSON
  `--> SARIF 2.1.0
```

## Components

### `run.py`

**What it is**

The repository entry point.

**How it works**

It adds `08_SCRIPTS` to `sys.path`, imports `uaaf_core.cli.main`, and exits with the integer returned by the CLI.

**Practical use**

```powershell
python run.py --help
```

No package installation is required for this repository-level entry point.

### CLI — `uaaf_core.cli`

**What it is**

The public command-line interface.

**Responsibilities**

- Define the public arguments.
- Normalize public values such as output formats, severities, and exclusions.
- Track which CLI values were explicitly supplied.
- Build the orchestrator with framework/plugin overrides.
- Dispatch one unified execution.
- Print execution/report summaries.
- Convert expected top-level failures into process exit code `2`.

The CLI does not implement auditor analysis rules.

### `ResolvedConfig`

**What it is**

The immutable canonical configuration produced for one UAAF execution.

**Responsibilities**

- Resolve framework defaults.
- Load optional configuration-file values.
- Apply explicit CLI overrides.
- Normalize and validate supported values.
- Resolve paths.
- Merge exclusions.
- Hold plugin defaults and plugin-specific configuration.
- Provide deterministic, redacted diagnostic snapshots.

Precedence:

```text
framework defaults < configuration file < explicit CLI arguments
```

Exclusions from file and CLI are merged rather than simply replaced.

### `UnifiedOrchestrator`

**What it is**

The core coordinator for one unified audit run.

**Responsibilities**

- Resolve global configuration.
- Discover plugins.
- Select `all` or a subset.
- Build plugin contexts.
- Execute selected plugins sequentially.
- Convert plugin failures into canonical failed results while allowing remaining selected plugins to continue.
- Consolidate findings and errors.
- Write requested reports.
- Determine exit code `0`, `1`, or `2`.

**Practical use**

The public interface is the CLI rather than direct construction for normal users:

```powershell
python run.py --project-path . --auditors architecture,testing
```

### `UAAFRegistry`

**What it is**

The canonical registry for dynamic plugin discovery and selection.

**Responsibilities**

- Discover plugin directories/modules.
- Validate plugin metadata and public contracts.
- Reject duplicate plugin IDs.
- Maintain deterministic canonical order.
- Build selector aliases from plugin ID, name, directory name, and audit type.
- Resolve explicit selectors.
- Return all plugins for `all`.
- Record non-fatal discovery issues separately from registered plugins.

Selection is deterministic. `all` cannot be mixed with explicit selectors.

### Auditor plugins

**What they are**

Independent domain analyzers implementing the plugin contract.

Current plugins:

```text
architecture-auditor
documentation-auditor
testing-auditor
configuration-auditor
ai-systems-auditor
```

Each plugin exposes a public:

```python
run(context) -> dict[str, Any]
```

The returned mapping must conform to UAAF's canonical audit-result contract.

See [Plugin reference](plugins.md).

### `AuditResult`

**What it is**

The canonical audit-result model shared by plugins, orchestration, and reporting.

It carries:

- plugin identity/version;
- audit type;
- status;
- summary;
- metrics;
- findings;
- execution errors;
- execution metadata.

A consolidated run uses the same canonical shape, allowing the reporting layer to remain independent from the individual auditor implementation.

### `RuntimeContext`

**What it is**

Runtime information assembled for the unified execution.

It provides framework/runtime context around the selected plugins and resolved configuration. It is distinct from each plugin's filtered `context` mapping.

### `ReportEngine`

**What it is**

The output layer for canonical UAAF results.

**Responsibilities**

- Render Markdown.
- Serialize JSON.
- Delegate SARIF 2.1.0 generation.
- Build stable report filenames from execution metadata and plugin/audit identity.
- Write reports to the configured output directory.

The default report formats are Markdown and JSON. SARIF is opt-in.

### `SarifExporter`

**What it is**

The SARIF 2.1.0 interoperability layer.

**Responsibilities**

- Translate canonical UAAF findings into SARIF rules/results.
- Map UAAF severities to SARIF levels.
- Produce safe project-relative POSIX artifact URIs.
- Avoid exporting unsafe/unresolvable source locations.
- Sanitize project-root path text in messages.
- Preserve deterministic rule/result structure.

See [Reporting and SARIF](reporting-and-sarif.md).

## Execution lifecycle

A normal CLI execution follows this sequence:

1. `run.py` calls `uaaf_core.cli.main()`.
2. CLI arguments are parsed and normalized.
3. `ResolvedConfig` combines defaults, configuration file, and explicit CLI values.
4. `UnifiedOrchestrator` asks `UAAFRegistry` to discover plugins.
5. The registry selects all plugins or the requested subset.
6. The orchestrator builds a context supported by each plugin.
7. Selected plugins execute sequentially.
8. Plugin mappings are validated/consolidated as canonical audit results.
9. `ReportEngine` writes each requested output format.
10. Exit-code policy is applied.

## Exit-code decision

Execution errors take precedence:

```text
plugin/runtime failure -> 2
matching --fail-on finding -> 1
otherwise -> 0
```

If `--fail-on` is empty, findings alone do not produce exit code `1`.

## Determinism

Deterministic behavior is an explicit design property across the implemented pipeline:

- registry order is canonical;
- selector processing is normalized;
- exclusions preserve stable first-seen order;
- findings are normalized/sorted within auditors where required;
- report serialization is deterministic for the same canonical input;
- SARIF rule construction is deterministic.

Timestamps and runtime duration naturally vary between executions.

## Boundaries

The current public architecture does not expose:

- parallel auditor execution;
- multiprocessing orchestration;
- incremental audit mode;
- persistent audit caching;
- dashboard or web UI;
- REST API;
- automatic remediation.

These are not required to understand or use the current UAAF CLI.

## Practical architecture example

For:

```powershell
python run.py `
  --project-path . `
  --auditors architecture,testing `
  --output-formats json `
  --fail-on error
```

the pipeline:

1. resolves the current directory as the project;
2. selects Architecture and Testing through the registry;
3. runs both auditors;
4. consolidates their findings;
5. writes one JSON report;
6. returns `1` only if an `error` finding exists, or `2` if execution itself failed.
