# Architecture Auditor Specification

**Version:** 1.0.0  
**Status:** MVP

## 1. Objective

Evaluate the structural integrity of a Python project and report deterministic
architecture violations without modifying the audited project.

## 2. Scope

The MVP analyzes local Python modules, packages, imports, dependency cycles and
configured architecture rules.

It does not evaluate documentation, security, performance, code style, external
package vulnerabilities or unused code.

## 3. Input

Required:

- `project_path`: existing project directory.

Optional:

- `ignored_directories`: additional directory names to exclude.
- `forbidden_imports`: import rules that must not occur.
- `layers`: ordered architectural layers and their module patterns.
- `require_package_initializers`: whether package directories require
  `__init__.py`; default `false`.

Unknown configuration fields must produce a validation error.

## 4. Default exclusions

- `.git`
- `.venv`
- `venv`
- `__pycache__`
- `node_modules`
- `build`
- `dist`

User exclusions are added to these defaults.

## 5. Rules

### ARCH_CIRCULAR_DEPENDENCY

Detect a cycle between local Python modules.

Severity: `error`.

One finding is produced per unique normalized cycle.

### ARCH_FORBIDDEN_IMPORT

Detect an import prohibited by `forbidden_imports`.

Severity: `error`.

One finding is produced per source module and prohibited import.

### ARCH_LAYER_VIOLATION

Detect a local dependency that violates the configured layer order.

Severity: `error`.

The rule runs only when `layers` is configured.

### ARCH_MISSING_PACKAGE_INITIALIZER

Detect a package directory without `__init__.py`.

Severity: `warning`.

The rule runs only when `require_package_initializers` is `true`.

## 6. Output

The auditor must always return the canonical `AuditResult`.

Required summary fields:

- `project_path`
- `modules`
- `packages`
- `dependency_cycles`

Required metrics:

- `python_file_count`
- `module_count`
- `package_count`
- `local_import_count`
- `dependency_edge_count`
- `circular_dependency_count`
- `forbidden_import_count`
- `layer_violation_count`
- `missing_package_initializer_count`
- `findings_count`

Every finding must use `AuditFinding` and include a stable code, severity, path,
message and details dictionary.

## 7. Determinism

Files, modules, dependencies, cycles and findings must be sorted before output.

Equivalent cycles must not create duplicate findings.

Imports that cannot be resolved to local modules are counted neither as local
dependencies nor as architecture violations, except when explicitly matched by
a forbidden-import rule.

Syntax or file-read failures must be reported through `errors`; they must not
terminate the complete audit.

## 8. Completion criteria

The MVP is complete when:

- it emits a valid `AuditResult`;
- all four rules have deterministic functional tests;
- default exclusions are verified;
- invalid input and configuration are tested;
- Runtime Pipeline integration passes;
- it has no dependency on another auditor.

Features outside this specification require a new specification version.
