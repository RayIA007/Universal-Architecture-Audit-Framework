# Universal Architecture Audit Framework (UAAF)

UAAF is a Python framework for running multiple static project auditors through one CLI, consolidating their findings into a canonical result, and exporting reports as Markdown, JSON, and optionally SARIF 2.1.0.

The current implementation focuses on architecture, documentation, testing structure, configuration files, and AI-system risks. UAAF is designed for developers and maintainers who want a repeatable, deterministic audit workflow that can run locally or in CI.

> **Documentation rule:** this documentation describes behavior implemented in the current repository. It does not present roadmap items as available features.

## Project status

Current validated project baseline:

- Five auditor plugins are available.
- Architecture Auditor version: `1.6.0`.
- Recorded full-suite baseline before Phase 3.6 documentation work: `820 passed`.
- Validated platform: Windows.
- Validated Python version: `3.14.6`.
- Validated pytest version: `9.1.1`.
- GitHub Actions workflow is implemented and remotely validated.
- SARIF 2.1.0 export is implemented and GitHub Code Scanning upload has been remotely validated.
- The repository is currently run from source; it is not published as a PyPI package.

## What UAAF audits

| Auditor | Main purpose |
|---|---|
| Architecture Auditor | Imports, dependencies, cycles, configured layers and forbidden imports, package initializers, cyclomatic complexity, module metrics, and conservative dead-code signals |
| Documentation Auditor | Root/package README coverage, public docstrings, and documentation placeholders |
| Testing Auditor | Structural relationship between source modules and tests, empty tests, and public APIs without an associated test |
| Configuration Auditor | Supported configuration files, syntax, hardcoded secrets, duplicated configuration values, and configurable required files |
| AI Systems Auditor | AI-library usage, hardcoded AI secrets/prompts, unprotected model/API calls, risky evaluation, generation settings, deprecated models, and agent/RAG safety signals |

See [Plugin reference](docs/plugins.md) for exact behavior, configuration notes, and practical examples.

## Canonical architecture

```text
CLI
 |
 v
ResolvedConfig
 |
 v
UnifiedOrchestrator
 |
 +--> UAAFRegistry --> discovered/selected plugins
 |
 v
Plugin execution
 |
 v
AuditResult
 |
 v
ReportEngine
 |
 +--> Markdown
 +--> JSON
 `--> SARIF 2.1.0
```

The CLI collects public arguments. `ResolvedConfig` applies deterministic configuration precedence. `UnifiedOrchestrator` discovers and selects plugins through `UAAFRegistry`, executes them, consolidates their canonical `AuditResult` data, and asks `ReportEngine` to write the requested output formats.

See [Architecture](docs/architecture.md).

## Requirements

### Validated environment

- Windows
- Python `3.14.6`

These are the environments currently validated by the project. Other platforms or Python versions are not claimed as validated by this documentation.

### Development/CI dependencies

The canonical GitHub Actions workflow installs:

```powershell
python -m pip install pytest==9.1.1 PyYAML==6.0.3
```

`pytest` is used for the test suite. `PyYAML` supports YAML parsing used by relevant auditing behavior.

## Installation from the repository

UAAF is currently executed from source. `pyproject.toml` does not define an installable package, so this documentation intentionally does **not** use `pip install uaaf`.

Clone the repository and enter its root directory:

```powershell
git clone <repository-url>
cd "Universal-Architecture-Audit-Framework"
```

To reproduce the currently validated development environment:

```powershell
python -m pip install pytest==9.1.1 PyYAML==6.0.3
```

Confirm the CLI:

```powershell
python run.py --help
```

## Quick start

Run every discovered auditor against the current directory and generate the default Markdown and JSON reports:

```powershell
python run.py `
  --project-path . `
  --auditors all `
  --output-formats markdown,json
```

By default, reports are written under:

```text
<UAAF_ROOT>/07_OUTPUTS
```

### CI-backed controlled example

The repository's GitHub Actions workflow uses the included sample project for a controlled smoke audit:

```powershell
python run.py `
  --project-path "12_EXAMPLES/sample_project" `
  --auditors "configuration" `
  --output-formats "markdown,json,sarif" `
  --output-dir "07_OUTPUTS"
```

The workflow itself uses a temporary runner directory rather than `07_OUTPUTS`, but the command above is convenient for local inspection.

## CLI reference

```text
python run.py [-h]
              [--project-path PROJECT_PATH]
              [--auditors AUDITORS]
              [--output-formats OUTPUT_FORMATS]
              [--config CONFIG]
              [--fail-on FAIL_ON]
              [--exclude DIRECTORIES]
              [--output-dir OUTPUT_DIR]
              [--plugins-dir PLUGINS_DIR]
              [--framework-root FRAMEWORK_ROOT]
```

| Option | Purpose | Default |
|---|---|---|
| `--project-path` | Directory to audit | current directory (`.`) |
| `--auditors` | Comma-separated auditor selectors or `all` | `all` |
| `--output-formats` | `markdown`, `json`, `sarif` | `markdown,json` |
| `--config` | Optional `.json`, `.toml`, `.yaml`, or `.yml` global config file | none |
| `--fail-on` | Severities that produce exit code `1` | empty |
| `--exclude` | Directory names to ignore; repeatable or comma-separated | empty |
| `--output-dir` | Report destination | `<UAAF_ROOT>/07_OUTPUTS` |
| `--plugins-dir` | Plugin directory override | `<UAAF_ROOT>/plugins` |
| `--framework-root` | Framework-root override | inferred from `uaaf_core` |

For complete CLI and configuration behavior, see [CLI and configuration](docs/cli-and-configuration.md).

## Selecting auditors

Run all discovered plugins:

```powershell
python run.py --project-path . --auditors all
```

Run a subset:

```powershell
python run.py `
  --project-path . `
  --auditors architecture,testing
```

Stable selectors include audit types and canonical plugin IDs:

| Audit type | Plugin ID |
|---|---|
| `architecture` | `architecture-auditor` |
| `documentation` | `documentation-auditor` |
| `testing` | `testing-auditor` |
| `configuration` | `configuration-auditor` |
| `ai_systems` | `ai-systems-auditor` |

`all` must be used by itself rather than combined with explicit selectors.

## Global configuration

UAAF resolves configuration with this precedence:

```text
framework defaults < configuration file < explicit CLI arguments
```

Exclusions are the exception to simple replacement: exclusions from the configuration file and explicit CLI are merged in stable first-seen order.

Supported global configuration files:

- JSON
- TOML
- TOML `[tool.uaaf]`
- YAML/YML using the deterministic subset implemented by UAAF

Example `uaaf.json`:

```json
{
  "project_path": ".",
  "auditors": ["architecture", "testing"],
  "output_formats": ["markdown", "json"],
  "fail_on": ["critical", "error"],
  "exclude": ["build", "dist"],
  "plugins": {
    "architecture-auditor": {
      "max_cyclomatic_complexity": 12
    }
  }
}
```

Run it with:

```powershell
python run.py --config uaaf.json
```

Paths written inside a configuration file are resolved relative to that file's directory. Plugin-specific configuration is validated/projected only into fields supported by the selected plugin.

See [CLI and configuration](docs/cli-and-configuration.md).

## Reporting

### Markdown

Human-readable audit report with findings, metrics, summary, and execution information.

### JSON

Machine-readable canonical representation of the UAAF audit result.

### SARIF 2.1.0

SARIF is optional and is not part of the historical default format set.

Generate all formats:

```powershell
python run.py `
  --project-path . `
  --output-formats markdown,json,sarif
```

The SARIF exporter:

- emits SARIF `2.1.0`;
- uses the official SARIF 2.1.0 Errata 01 schema URI;
- creates deterministic rules/results from UAAF findings;
- maps UAAF severities to SARIF levels;
- exports safe project-relative POSIX artifact URIs;
- redacts absolute project-root text from messages;
- omits a finding from SARIF `results[]` when no safe exportable artifact URI exists;
- preserves that finding in UAAF's canonical result and Markdown/JSON reporting;
- does not invent source locations to satisfy SARIF consumers.

See [Reporting and SARIF](docs/reporting-and-sarif.md).

## Severities

UAAF uses four canonical finding severities:

| Severity | Typical meaning |
|---|---|
| `critical` | Highest-impact problem, including findings that may represent serious security or integrity risk |
| `error` | Defect or rule violation that should normally be addressed |
| `warning` | Potential issue, maintainability problem, or policy concern |
| `info` | Informational observation |

The severity itself does not automatically make the CLI fail. Use `--fail-on` to define the severities that should produce exit code `1`.

Example:

```powershell
python run.py `
  --project-path . `
  --fail-on critical,error
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Execution completed without an execution failure and no finding matched `--fail-on` |
| `1` | At least one finding matched a severity configured in `--fail-on` |
| `2` | Configuration/CLI/runtime execution failed, or an auditor execution returned a failure/error state |

Execution failures take precedence over finding-based failure.

## Exclusions

`--exclude` accepts **directory names**, not paths.

Valid:

```powershell
python run.py `
  --project-path . `
  --exclude generated,cache `
  --exclude build
```

Invalid:

```text
--exclude generated/cache
```

Configuration-file exclusions and explicit CLI exclusions are merged.

## Practical examples

### Audit everything with default reports

```powershell
python run.py --project-path . --auditors all
```

### Run only architecture and testing

```powershell
python run.py `
  --project-path . `
  --auditors architecture,testing
```

### Generate only JSON

```powershell
python run.py `
  --project-path . `
  --output-formats json
```

### Generate SARIF for Code Scanning interoperability

```powershell
python run.py `
  --project-path . `
  --output-formats markdown,json,sarif
```

### Use a configuration file

```powershell
python run.py --config uaaf.json
```

### Fail CI on critical or error findings

```powershell
python run.py `
  --project-path . `
  --fail-on critical,error
```

### Write reports to a custom directory

```powershell
python run.py `
  --project-path . `
  --output-dir reports
```

## GitHub Actions and Code Scanning

The repository contains:

```text
.github/workflows/uaaf-ci.yml
```

The canonical quality job currently:

- runs on `windows-latest`;
- uses Python `3.14.6`;
- installs pinned `pytest==9.1.1` and `PyYAML==6.0.3`;
- executes `python -m pytest -q`;
- validates `python run.py --help`;
- runs a controlled UAAF smoke audit against `12_EXAMPLES/sample_project`;
- verifies Markdown, JSON, and SARIF output;
- validates the SARIF version and guards against absolute Windows paths;
- uploads SARIF with `github/codeql-action/upload-sarif@v4`;
- grants `contents: read` and the job-level `security-events: write` permission needed for Code Scanning;
- skips SARIF upload for pull requests originating from forks.

See [Development and CI](docs/development.md) and [Reporting and SARIF](docs/reporting-and-sarif.md).

## Testing

Run the complete suite:

```powershell
python -m pytest -q
```

Recorded baseline before Phase 3.6 documentation work:

```text
820 passed
```

After documentation changes, the full suite should still pass before the phase is closed.

## Project structure

Simplified public view:

```text
Universal-Architecture-Audit-Framework/
├── .github/workflows/       # CI workflow
├── 00_DOCUMENTATION/        # Existing architecture/governance/methodology material
├── 07_OUTPUTS/              # Default report destination
├── 08_SCRIPTS/
│   └── uaaf_core/           # CLI, config, orchestrator, registry, runtime, reporting
├── 09_TESTS/                # Unit and integration tests
├── 12_EXAMPLES/
│   └── sample_project/      # Controlled example used by CI
├── plugins/                 # Five current auditor plugins
├── docs/                    # Public technical documentation
├── README.md
└── run.py                   # Repository CLI entry point
```

`00_DOCUMENTATION/` remains part of the repository's existing internal/architectural documentation structure. The `docs/` directory is the public, implementation-focused technical reference and does not require reorganizing the existing tree.

## Current limitations

The public documentation intentionally records current boundaries:

- Windows is the validated platform.
- Python `3.14.6` is the validated interpreter.
- UAAF is currently run from the repository rather than installed from PyPI.
- Auditor orchestration is sequential.
- SARIF only exports findings with a safe artifact location.
- No public incremental-audit mode is exposed by the current CLI.
- No public persistent-cache mode is exposed by the current CLI.
- No public dashboard, REST API, or web UI is part of the current CLI workflow.
- Compatibility with unvalidated operating systems or Python versions is not claimed.

These limitations describe the current implementation; they are not promises about future roadmap work.

## Troubleshooting

### `python run.py --help` fails

Confirm that you are in the repository root and using the validated Python environment.

### Plugin not found

Use `--auditors all` or one of the documented audit types/plugin IDs. If overriding `--plugins-dir`, confirm that it points to a valid plugin directory.

### Configuration file rejected

Confirm that the extension is `.json`, `.toml`, `.yaml`, or `.yml`, and that values use the types expected by UAAF. TOML may use `[tool.uaaf]`; do not mix conflicting direct UAAF fields with `[tool.uaaf]`.

### `--exclude` is rejected

Supply directory names only, not paths.

### Exit code `1`

At least one finding matched a severity configured by `--fail-on`.

### Exit code `2`

An expected configuration/CLI/runtime error occurred, or an auditor execution entered a failure/error state. Check stderr and the generated audit data where available.

### SARIF contains fewer results than Markdown/JSON

A canonical finding may not have a safe exportable source URI. UAAF keeps the finding in its canonical result and Markdown/JSON output but omits it from SARIF `results[]` rather than inventing a location.

## Contributing

Keep changes focused and preserve public contracts.

A simple contribution workflow is:

1. Create a branch.
2. Make one focused change.
3. Add or update tests when behavior changes.
4. Run `python run.py --help` when CLI-facing behavior is involved.
5. Run `python -m pytest -q`.
6. Run `git diff --check`.
7. Review the relevant diff.
8. Open a pull request.

No additional governance process is implied by this section.

## Public technical documentation

- [Architecture](docs/architecture.md)
- [CLI and configuration](docs/cli-and-configuration.md)
- [Plugin reference](docs/plugins.md)
- [Reporting and SARIF](docs/reporting-and-sarif.md)
- [Development, CI, troubleshooting, and limitations](docs/development.md)
