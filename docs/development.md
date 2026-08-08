# Development, CI, Troubleshooting, and Limitations

## Validated environment

Current validated environment:

```text
Operating system: Windows
Python: 3.14.6
pytest: 9.1.1
```

The public documentation does not claim that other platforms or Python versions are validated.

## Repository setup

UAAF currently runs directly from the repository.

`pyproject.toml` is empty and does not define a distributable package, so there is no documented `pip install uaaf` flow.

To match the canonical CI development dependencies:

```powershell
python -m pip install pytest==9.1.1 PyYAML==6.0.3
```

Verify:

```powershell
python --version
python -m pip --version
python run.py --help
```

## Testing

Complete suite:

```powershell
python -m pytest -q
```

Current validated full-suite baseline:

```text
820 passed
```

Documentation-only changes should not introduce functional regressions.

## Canonical CI workflow

File:

```text
.github/workflows/uaaf-ci.yml
```

Triggers:

```text
push -> main
pull_request -> main
workflow_dispatch
```

The workflow deliberately does not use privileged/unneeded triggers such as `pull_request_target`.

### Quality job

The quality job:

1. runs on `windows-latest`;
2. sets up Python `3.14.6` x64;
3. validates Python and pip;
4. installs pinned `pytest==9.1.1` and `PyYAML==6.0.3`;
5. runs `python -m pytest -q`;
6. runs `python run.py --help`;
7. executes a controlled UAAF smoke audit;
8. verifies Markdown/JSON/SARIF outputs;
9. validates key SARIF safety properties;
10. uploads SARIF to GitHub Code Scanning when the event is eligible.

### Controlled smoke project

The CI smoke uses:

```text
12_EXAMPLES/sample_project
```

and the Configuration Auditor.

It writes to the runner's temporary directory, so the canonical workflow does not pollute repository `07_OUTPUTS/`.

### CI permissions

Top-level:

```yaml
permissions:
  contents: read
```

Quality job:

```yaml
permissions:
  contents: read
  security-events: write
```

The workflow does not reference secrets for SARIF upload and does not grant repository-content write access.

### Fork behavior

GitHub Code Scanning upload runs only when:

- the event is not a pull request; or
- the pull request originates from the same repository.

This prevents the SARIF upload step from running for fork-origin pull requests.

## Validation before a documentation commit

Recommended documentation-change validation sequence:

```powershell
python run.py --help
```

```powershell
python -m pytest -q
```

```powershell
git diff --check
```

```powershell
git status --short
```

Then review the relevant diff and stage only the files intentionally changed.

## Simplified project structure

```text
Universal-Architecture-Audit-Framework/
├── .github/workflows/
│   └── uaaf-ci.yml
├── 00_DOCUMENTATION/
├── 01_CONFIG/
├── 02_SCHEMAS/
├── 03_RULES/
├── 04_AUDIT_PROFILES/
├── 05_INPUTS/
├── 06_WORKSPACES/
├── 07_OUTPUTS/
├── 08_SCRIPTS/
│   └── uaaf_core/
├── 09_TESTS/
├── 10_TEMPLATES/
├── 11_LOGS/
├── 12_EXAMPLES/
│   └── sample_project/
├── 13_PLUGINS/
├── 90_SPECIFICATIONS/
├── plugins/
│   ├── architecture/
│   ├── documentation/
│   ├── testing/
│   ├── configuration/
│   └── ai_systems/
├── docs/
├── README.md
├── run.py
└── pyproject.toml
```

`00_DOCUMENTATION/` is intentionally not reorganized as part of public-documentation work. The public `docs/` layer documents the current implementation without requiring cosmetic tree changes.

## Troubleshooting

### CLI cannot start

Symptom:

```text
python run.py --help
```

does not complete successfully.

Check:

- current directory is the UAAF repository root;
- Python is available;
- the repository contains `08_SCRIPTS/uaaf_core`.

`run.py` bootstraps `08_SCRIPTS` before importing the CLI.

### Project path does not exist

`--project-path` must resolve to an existing directory.

Example:

```powershell
python run.py --project-path "C:\Projects\existing-project"
```

### Unknown auditor selector

Use:

```text
all
architecture
documentation
testing
configuration
ai_systems
```

or their canonical plugin IDs.

`all` cannot be mixed with explicit selectors.

### Unknown output format

Only:

```text
markdown
json
sarif
```

are public formats. `md` is accepted as a normalization alias for Markdown.

### Invalid `--fail-on`

Only:

```text
critical
error
warning
info
```

are valid severities.

### Invalid exclusion

Exclusions are directory names only.

Valid:

```text
generated
cache
build
```

Invalid:

```text
generated/cache
C:\project\build
.
..
```

### Configuration file does not load

Global config files must use:

```text
.json
.toml
.yaml
.yml
```

For TOML, use either direct UAAF fields or `[tool.uaaf]`. Do not provide conflicting versions of the same UAAF configuration.

Relative paths in a configuration file are resolved from that file's directory.

### Exit code `1`

Meaning:

A finding severity matched `--fail-on`.

Example:

```powershell
python run.py --fail-on critical,error
```

A critical or error finding can return `1`.

### Exit code `2`

Meaning:

An execution/configuration/runtime failure occurred, or a selected auditor returned a failure/error state.

The CLI writes an error message to stderr for top-level expected failures.

### Configuration Auditor reports required files

The Configuration Auditor has default required filenames:

```text
pyproject.toml
.env
config.yaml
```

If those files are not part of the audited project's intended contract, override `required_config_files` for that plugin.

Example:

```yaml
plugins:
  configuration-auditor:
    required_config_files:
      - pyproject.toml
```

### SARIF has fewer results than Markdown/JSON

This can be expected when a canonical finding has no safe exportable artifact location.

UAAF preserves the canonical finding but omits that item from SARIF `results[]`.

### Code Scanning upload is skipped on a fork PR

This is intentional. The workflow protects fork-origin pull requests by skipping the SARIF upload step.

## Current limitations

### Platform validation

Windows is the canonical validated platform. The project does not currently claim validated cross-platform behavior.

### Packaging

UAAF is not currently documented as a PyPI package and has no public installer workflow.

### Orchestration

Selected plugins execute sequentially. There is no public parallel or multiprocessing mode in the current CLI.

### Incremental analysis and caching

The public CLI does not expose:

- incremental auditing;
- persistent audit caching;
- a cache-management command.

### User interfaces/services

The current public CLI workflow does not expose:

- web dashboard;
- REST API;
- web UI.

### SARIF projection

SARIF requires safe source locations for exportable results. Findings without a safe URI remain available in canonical UAAF/Markdown/JSON data but may be absent from SARIF results.

### Static-analysis limits

Several auditors intentionally use static heuristics.

Examples:

- conservative dead-code signals cannot prove behavior that depends on dynamic references;
- structural testing analysis is not runtime line coverage;
- AI-system findings indicate patterns that warrant review and are not proof of an exploitable vulnerability.

## Contributing

Keep contributions focused.

1. Create a branch.
2. Make the intended change.
3. Add/update tests when behavior changes.
4. Run relevant targeted tests.
5. Run the full suite.
6. Run `git diff --check`.
7. Review changed files.
8. Stage only the intended files.
9. Open a pull request.

Avoid unrelated architecture or process changes in a documentation-only contribution.
