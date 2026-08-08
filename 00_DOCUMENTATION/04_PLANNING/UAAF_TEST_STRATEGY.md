# UAAF Test Strategy
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-PLAN-002
**Version:** 1.0
**Status:** Maintained
**Classification:** Planning and Quality
**Owner:** Architecture

---

## 1. Purpose

Define the permanent validation strategy for UAAF development and documentation changes.

## 2. Current Baseline

At the completed Phase 3 baseline:

```text
820 tests passed
Windows validated
Python 3.14.6
pytest 9.1.1
```

The baseline count is a regression reference, not a guarantee that future versions will always contain exactly 820 tests.

## 3. Test Layers

UAAF uses:

- unit tests for contracts, components, auditors, configuration, reporting, registry, CLI, and SARIF;
- integration tests for cross-component pipelines;
- smoke execution in CI;
- workflow-contract tests for CI behavior where implemented.

## 4. Architecture Auditor Regression Suites

Recorded suites include:

- Suite A — contract/configuration;
- Suite B — discovery/index;
- Suite C — imports/graph;
- Suite D — architectural rules;
- Suite E — robustness;
- Suite F — runtime pipeline integration;
- Suite L — semantic features.

## 5. Full Regression Command

```powershell
python -m pytest -q
```

## 6. CLI Contract Check

```powershell
python run.py --help
```

## 7. Documentation-Only Change Validation

Documentation-only work should verify at minimum:

```powershell
git diff --check
python -m pytest -q
git status --short
```

Review the exact diff and stage only intended files.

## 8. CI Validation

The canonical workflow on `main` validates:

- Python environment;
- full pytest suite;
- CLI help;
- controlled Configuration Auditor smoke run;
- Markdown/JSON/SARIF output;
- SARIF safety;
- eligible Code Scanning upload.

## 9. Regression Policy

A change shall not intentionally reduce validated behavior without an explicit compatibility/architecture decision.

If a test count changes, interpret the test results and scope rather than treating the raw count alone as quality proof.

## 10. Test Data Safety

Simulated secrets used in tests are fixtures, not real credentials.

Security-related findings from intentionally adversarial fixtures must be interpreted within test context.

---
# End of Document
