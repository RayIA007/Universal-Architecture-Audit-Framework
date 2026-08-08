# CLI and Global Configuration

This document is the public reference for UAAF command-line execution and `ResolvedConfig`.

## CLI

Show the canonical help:

```powershell
python run.py --help
```

Current public options:

| Option | Accepted form | Default |
|---|---|---|
| `--project-path` | directory path | `.` |
| `--auditors` | comma-separated selectors or `all` | `all` |
| `--output-formats` | comma-separated `markdown,json,sarif` | `markdown,json` |
| `--config` | `.json`, `.toml`, `.yaml`, `.yml` file | none |
| `--fail-on` | comma-separated severities | empty |
| `--exclude` | directory names; repeatable/CSV | empty |
| `--output-dir` | directory path | `<UAAF_ROOT>/07_OUTPUTS` |
| `--plugins-dir` | directory path | `<UAAF_ROOT>/plugins` |
| `--framework-root` | directory path | inferred |

### Project path

```powershell
python run.py --project-path "C:\Projects\my-project"
```

The target must exist and be a directory.

### Auditor selection

Run all:

```powershell
python run.py --auditors all
```

Run a subset:

```powershell
python run.py --auditors architecture,testing
```

Documented stable selectors:

| Audit type | Canonical plugin ID |
|---|---|
| `architecture` | `architecture-auditor` |
| `documentation` | `documentation-auditor` |
| `testing` | `testing-auditor` |
| `configuration` | `configuration-auditor` |
| `ai_systems` | `ai-systems-auditor` |

The registry also builds aliases from plugin metadata, but using audit types or canonical plugin IDs keeps commands explicit.

`all` cannot be combined with explicit selectors.

### Output formats

Default:

```text
markdown,json
```

Supported:

```text
markdown
json
sarif
```

`md` is normalized to `markdown` by the CLI/reporting layer.

Examples:

```powershell
python run.py --output-formats json
```

```powershell
python run.py --output-formats markdown,json,sarif
```

Unknown formats are rejected.

### `--fail-on`

Supported canonical severities:

```text
critical
error
warning
info
```

Example:

```powershell
python run.py --fail-on critical,error
```

If a selected auditor completes with a matching finding, the final process code is `1`.

If no severity is configured, findings do not produce code `1`.

Execution failures produce `2` and take precedence.

### Exclusions

Exclusions must be directory **names**, not paths.

Valid:

```powershell
python run.py --exclude generated,cache --exclude build
```

Invalid:

```text
--exclude generated/cache
--exclude C:\project\build
```

Case is preserved. Duplicate names are removed in stable first-seen order.

### Output directory

```powershell
python run.py --output-dir reports
```

If not provided, UAAF writes under:

```text
<UAAF_ROOT>/07_OUTPUTS
```

### Plugin directory override

```powershell
python run.py --plugins-dir custom_plugins
```

This is primarily useful for isolated deployments/tests. Normal repository usage should use the canonical `plugins/` directory.

### Framework-root override

```powershell
python run.py --framework-root "C:\Path\To\UAAF"
```

Normal repository usage does not need this because the framework root is inferred from `uaaf_core`.

## Global configuration

### Precedence

For ordinary fields:

```text
framework defaults < configuration file < explicit CLI arguments
```

Only CLI values explicitly present in the invocation override the configuration file. Parser defaults do not accidentally overwrite file values.

Exclusions are merged:

```text
file exclusions + explicit CLI exclusions
```

with stable first-seen deduplication.

### Supported file formats

Global UAAF configuration supports:

- `.json`
- `.toml`
- `.yaml`
- `.yml`

TOML may place UAAF configuration under `[tool.uaaf]`.

The YAML loader intentionally supports a deterministic subset rather than promising every YAML feature.

### Global keys

Current recognized global keys include:

```text
project_path
auditors
output_formats
fail_on
exclude
ignored_directories
output_dir
plugins_dir
framework_root
defaults
global
plugins
```

`ignored_directories` is an alias that contributes to global exclusions.

`global` is an alias for plugin `defaults`.

A mapping-valued `auditors` field is a compatibility alias for plugin configuration. For new documentation/configuration, prefer the explicit `plugins` field.

### JSON example

```json
{
  "project_path": ".",
  "auditors": ["architecture", "testing"],
  "output_formats": ["markdown", "json"],
  "fail_on": ["critical", "error"],
  "exclude": ["generated", "cache"],
  "output_dir": "reports",
  "plugins": {
    "architecture-auditor": {
      "max_cyclomatic_complexity": 12
    }
  }
}
```

Run:

```powershell
python run.py --config uaaf.json
```

### YAML example

```yaml
project_path: .
auditors:
  - architecture
  - testing

output_formats:
  - markdown
  - json

fail_on:
  - critical
  - error

exclude:
  - generated
  - cache

plugins:
  architecture-auditor:
    max_cyclomatic_complexity: 12
```

Run:

```powershell
python run.py --config uaaf.yaml
```

### TOML example

Direct UAAF document:

```toml
project_path = "."
auditors = ["architecture", "testing"]
output_formats = ["markdown", "json"]
fail_on = ["critical", "error"]
exclude = ["generated", "cache"]

[plugins.architecture-auditor]
max_cyclomatic_complexity = 12
```

Or a `pyproject.toml`-style table:

```toml
[tool.uaaf]
project_path = "."
auditors = ["architecture", "testing"]
output_formats = ["markdown", "json"]
fail_on = ["critical", "error"]
exclude = ["generated", "cache"]

[tool.uaaf.plugins.architecture-auditor]
max_cyclomatic_complexity = 12
```

Do not provide conflicting direct UAAF fields and `[tool.uaaf]` data in the same TOML document.

## Path resolution

Paths written in a configuration file are resolved relative to the configuration file's directory.

Example layout:

```text
config/
├── uaaf.json
├── target-project/
└── reports/
```

A configuration file inside `config/` can use:

```json
{
  "project_path": "target-project",
  "output_dir": "reports"
}
```

and both paths resolve from `config/`.

CLI paths are interpreted from the execution context rather than from the config file.

## Plugin configuration

`ResolvedConfig` stores:

- `plugin_defaults`: common plugin context values;
- `plugin_configs`: per-plugin mappings.

The orchestrator projects only supported context fields into each selected plugin.

Example:

```yaml
plugins:
  architecture-auditor:
    max_cyclomatic_complexity: 15

  testing-auditor:
    require_test_for_public_api: true
```

See [Plugin reference](plugins.md) for supported fields.

## Exit codes

| Code | Condition |
|---|---|
| `0` | no execution failure and no finding matches `fail_on` |
| `1` | at least one finding matches `fail_on` |
| `2` | plugin/runtime/configuration/CLI execution failure |

A plugin result with errors, `failed`, or `completed_with_errors` causes exit code `2`.

## Practical configurations

### Local exploratory audit

Do not fail on findings:

```powershell
python run.py `
  --project-path . `
  --auditors all
```

### CI quality gate

```powershell
python run.py `
  --project-path . `
  --auditors all `
  --fail-on critical,error `
  --output-formats markdown,json,sarif
```

### Exclude generated directories

```powershell
python run.py `
  --project-path . `
  --exclude generated,cache,dist
```

### Override only one file value

If `uaaf.json` selects all auditors but you want only testing for one run:

```powershell
python run.py `
  --config uaaf.json `
  --auditors testing
```

Because `--auditors` is explicit, it overrides the file value.
