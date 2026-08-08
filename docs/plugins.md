# Auditor Plugin Reference

UAAF currently discovers five auditor plugins from the repository `plugins/` directory.

Each plugin exposes the canonical public contract:

```python
run(context) -> dict[str, Any]
```

The returned mapping conforms to the UAAF audit-result model and is consolidated by the unified orchestrator.

## Architecture Auditor

```text
Plugin ID: architecture-auditor
Audit type: architecture
Version: 1.6.0
```

### What it is

A static Python architecture analyzer.

### What it does

It:

- discovers Python modules/packages;
- extracts imports;
- builds dependency edges;
- detects dependency cycles;
- validates configured architecture layers;
- validates configured forbidden imports;
- can require package `__init__.py` initializers;
- calculates per-module structural metrics;
- calculates cyclomatic complexity for supported symbols;
- flags complexity above a configurable threshold;
- performs conservative dead-code analysis for unused import bindings and module-level functions with no statically demonstrable project reference.

Important rule behavior includes:

```text
ARCH-CYCLE-001
ARCH-LAYER-001
ARCH-FORBIDDEN-001
ARCH-INIT-001
ARCH-COMPLEX-001
ARCH-DEAD-001
```

The default maximum cyclomatic-complexity threshold is `10`.

### How to use it

```powershell
python run.py `
  --project-path . `
  --auditors architecture
```

With configuration:

```yaml
plugins:
  architecture-auditor:
    max_cyclomatic_complexity: 12
```

Layer/forbidden-import/package-initializer checks are configuration-driven rather than unconditional.

### Practical uses

- Detect a dependency cycle between two packages.
- Enforce a rule that presentation code cannot import persistence internals.
- Block a forbidden dependency.
- Identify functions whose complexity exceeds the agreed threshold.
- Review unused imports or likely unreferenced module-level functions.
- Inspect module dependency/size metrics during architecture review.

The dead-code rule is intentionally conservative; it reports static evidence, not proof that dynamically referenced code is unreachable.

---

## Documentation Auditor

```text
Plugin ID: documentation-auditor
Audit type: documentation
Version: 1.0.0
```

### What it is

A static documentation-completeness and documentation-quality auditor for Python projects.

### What it does

It detects:

- missing root/package README files;
- missing module docstrings;
- missing public class docstrings;
- missing public function docstrings;
- documentation placeholders such as `TODO`, `FIXME`, `Lorem ipsum`, `XXX`, `HACK`, and `PLACEHOLDER`.

Canonical findings:

```text
DOC-README-001
DOC-DOCSTRING-001
DOC-PLACEHOLDER-001
```

By default, package README checks and module/class/function docstring checks are enabled.

### Supported plugin fields

```text
ignored_directories
require_readme_in_packages
require_module_docstrings
require_class_docstrings
require_function_docstrings
placeholder_patterns
readme_filenames
```

### How to use it

```powershell
python run.py `
  --project-path . `
  --auditors documentation
```

Example configuration:

```yaml
plugins:
  documentation-auditor:
    require_readme_in_packages: true
    require_module_docstrings: true
    require_class_docstrings: true
    require_function_docstrings: true
```

### Practical uses

- Check whether public Python packages have basic README documentation.
- Find public APIs added without docstrings.
- Detect unfinished documentation markers before release.
- Include documentation completeness in a CI audit.

---

## Testing Auditor

```text
Plugin ID: testing-auditor
Audit type: testing
Version: 1.0.0
```

### What it is

A structural test-coverage auditor.

It does **not** calculate runtime line/branch coverage percentages. Instead it analyzes the relationship between source code and test structure.

### What it does

It:

- discovers Python source and test files;
- recognizes default test patterns `test_*.py` and `*_test.py`;
- recognizes default test directories `tests`, `test`, and `09_TESTS`;
- finds source modules without a corresponding test file;
- detects empty/placeholder test functions;
- by default checks public classes/functions for an associated test reference.

Canonical findings:

```text
TEST-MISSING-001
TEST-EMPTY-001
TEST-OUTDATED-001
```

`TEST-EMPTY-001` is an `error`; the missing-test and public-API findings are warnings.

### Supported plugin fields

```text
ignored_directories
test_file_patterns
test_directories
source_directories
require_test_for_public_api
```

`require_test_for_public_api` defaults to `true`.

### How to use it

```powershell
python run.py `
  --project-path . `
  --auditors testing
```

Example configuration:

```yaml
plugins:
  testing-auditor:
    test_directories:
      - tests
    require_test_for_public_api: true
```

### Practical uses

- Find a newly created module that has no expected test file.
- Find `test_*` functions that contain only `pass`/placeholder content.
- Identify public APIs without a structurally associated test.
- Enforce basic test organization before merging.

---

## Configuration Auditor

```text
Plugin ID: configuration-auditor
Audit type: configuration
Version: 1.0.0
```

### What it is

A static auditor for project configuration files.

### What it does

Default discovered configuration extensions:

```text
.json
.yaml
.yml
.toml
.ini
.env
.cfg
```

It checks:

- parseable syntax for supported structured formats;
- possible hardcoded secrets/credentials;
- duplicated configuration values across files;
- configurable required configuration files.

Canonical findings:

```text
CONFIG-MISSING-001
CONFIG-INVALID-001
CONFIG-SECRET-001
CONFIG-DUPLICATE-001
```

Notable severities:

- invalid configuration syntax: `error`;
- hardcoded secret: `critical`;
- missing required configuration and duplicates: `warning`.

Default required filenames currently include:

```text
pyproject.toml
.env
config.yaml
```

These defaults are auditor policy and can be overridden through plugin configuration.

### Supported plugin fields

```text
ignored_directories
config_extensions
required_config_files
secret_patterns
```

### How to use it

```powershell
python run.py `
  --project-path . `
  --auditors configuration
```

Example configuration that changes required files:

```yaml
plugins:
  configuration-auditor:
    required_config_files:
      - pyproject.toml
```

### Practical uses

- Detect malformed JSON/TOML/YAML configuration.
- Identify credential-like values committed into configuration files.
- Detect the same configuration value duplicated across multiple files.
- Enforce the presence of project-specific configuration files.

---

## AI Systems Auditor

```text
Plugin ID: ai-systems-auditor
Audit type: ai_systems
Version: 1.0.0
```

### What it is

A static Python auditor focused on common implementation risks in LLM/AI applications.

### What it does

It analyzes Python files for:

- imports associated with configured AI libraries/frameworks;
- possible hardcoded AI/API secrets, with matched secret text redacted in the finding data;
- long hardcoded strings that look like prompts;
- AI generation/API calls without the expected protection/retry/error-handling evidence;
- potentially unsafe evaluation of values derived from LLM outputs;
- suspicious generation configuration;
- configured deprecated model identifiers;
- autonomous-agent patterns without human-safeguard evidence;
- retrieval/RAG patterns without source-validation evidence.

The auditor records separate metrics for imports, secrets, prompts, unprotected API calls, LLM-evaluation risks, generation configuration, deprecated models, safety findings, and parse errors.

### Supported plugin fields

```text
ignored_directories
ai_libraries
secret_patterns
prompt_min_chars
max_reasonable_tokens
deprecated_models
```

The default hardcoded-prompt minimum length is `200` characters and the default maximum-reasonable-token threshold is `32768`.

### How to use it

```powershell
python run.py `
  --project-path . `
  --auditors ai_systems
```

### Practical uses

- Find an API key embedded directly in Python source.
- Find a large system prompt embedded in application code.
- Review model calls that do not show local exception/retry protection.
- Identify use of a model identifier configured as deprecated.
- Review agent workflows that appear autonomous without human approval markers.
- Review RAG/retrieval flows lacking source-validation markers.

These checks are static heuristics. A finding is a review signal, not proof of a production vulnerability.

---

## Run all plugins

```powershell
python run.py `
  --project-path . `
  --auditors all
```

## Run a subset

```powershell
python run.py `
  --project-path . `
  --auditors architecture,documentation,ai_systems
```

## Shared exclusions

The unified CLI projects global exclusions into supported plugin contexts:

```powershell
python run.py `
  --project-path . `
  --auditors all `
  --exclude generated,cache,dist
```

Only directory names are accepted by the global exclusion option.
