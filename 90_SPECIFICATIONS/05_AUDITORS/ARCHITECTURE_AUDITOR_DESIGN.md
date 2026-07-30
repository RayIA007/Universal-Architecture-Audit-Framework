# Architecture Auditor Design

**Version:** 1.0.0  
**Status:** MVP

## 1. Design goal

Implement the Architecture Auditor with the minimum structure required to
support the approved specification without creating a premature shared
framework.

## 2. Plugin structure

```text
plugins/architecture/
├── plugin.yaml
├── __init__.py
└── architecture_auditor.py
```

The MVP remains in one implementation module. Extraction into shared UAAF
components is allowed only after a second auditor requires the same behavior.

## 3. Responsibilities

`architecture_auditor.py` will contain:

- input validation;
- project file discovery;
- Python module indexing;
- AST import extraction;
- local dependency resolution;
- cycle detection;
- configured rule evaluation;
- `AuditFinding` construction;
- canonical `AuditResult` construction.

Internal helper functions are preferred over classes unless persistent state or
a clear interface is required.

## 4. Execution flow

1. Validate `project_path` and optional configuration.
2. Discover Python files using default and user exclusions.
3. Build a deterministic module index.
4. Parse imports with `ast`.
5. Resolve imports that reference local modules.
6. Build the local dependency graph.
7. Evaluate the four MVP rules.
8. Sort findings and output data.
9. Return `AuditResult.to_dict()`.

## 5. Internal data

Use standard Python structures only:

- `dict[str, Path]` for the module index;
- `dict[str, set[str]]` for the dependency graph;
- `list[AuditFinding]` for findings;
- `list[str]` for recoverable errors.

No external graph library is required.

## 6. Rule implementation

Each rule is implemented as one private function:

- `_find_circular_dependencies`
- `_find_forbidden_imports`
- `_find_layer_violations`
- `_find_missing_package_initializers`

Each function receives prepared data and returns findings without reading or
modifying files directly.

## 7. Error handling

- Invalid required input stops execution with a validation error.
- Syntax and file-read failures are added to `errors`.
- One unreadable or invalid Python file must not stop the complete audit.
- The auditor never modifies the audited project.

## 8. Determinism

All file paths, module names, dependencies, cycles, findings and summary lists
must be normalized and sorted before serialization.

Cycle detection must produce one canonical representation per unique cycle.

## 9. Shared-component rule

No reusable scanner, resolver or graph package will be created during this MVP.

A component may move into shared UAAF code only when:

1. a second auditor requires the same behavior; and
2. the extracted interface can be defined without auditor-specific rules.

## 10. Initial implementation sequence

1. Create plugin manifest and skeleton.
2. Add discovery and module indexing.
3. Add import extraction and local dependency graph.
4. Add the four rules.
5. Build canonical `AuditResult`.
6. Add deterministic functional tests.
7. Add Runtime Pipeline integration validation.

Features not required by the approved specification remain out of scope.
