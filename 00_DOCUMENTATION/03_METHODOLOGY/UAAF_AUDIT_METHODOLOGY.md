# UAAF Audit Methodology
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-MTH-001
**Version:** 1.0
**Status:** Maintained
**Classification:** Methodology
**Owner:** Architecture

---

## 1. Purpose

Define the repeatable methodology for current UAAF audits.

## 2. Governing References

- `../02_ARCHITECTURE/UAAF_PIPELINE_ARCHITECTURE.md`
- `../02_ARCHITECTURE/UAAF_DATA_MODEL.md`
- `../../docs/cli-and-configuration.md`
- `../../docs/plugins.md`

## 3. Audit Preparation

Before execution:

1. identify the project directory;
2. select `all` or an explicit auditor subset;
3. define optional configuration;
4. define exclusions by directory name;
5. define requested report formats;
6. define `fail_on` severities only if a quality gate is desired.

## 4. Canonical Execution

```powershell
python run.py --project-path . --auditors all
```

Current default report formats are Markdown and JSON.

## 5. Auditor Interpretation

Each plugin performs static analysis within its documented scope.

Findings are review signals based on implemented rules/heuristics.

They are not automatically equivalent to runtime test coverage, confirmed vulnerabilities, business impact, or exploitability.

## 6. Finding Handling

For each finding review:

- plugin/audit source;
- code;
- severity;
- path;
- message;
- structured details.

Use the plugin reference to understand rule scope and known heuristic limits.

## 7. Execution Errors

Execution errors are distinct from findings.

A plugin/runtime/configuration execution failure produces exit code `2` semantics and should be resolved before interpreting the run as a complete audit.

## 8. Quality Gates

`--fail-on` converts selected finding severities into exit code `1`.

Example:

```powershell
python run.py --project-path . --fail-on critical,error
```

Without `--fail-on`, findings alone do not fail the process.

## 9. Reports

Use:

- Markdown for human review;
- JSON for canonical machine-readable data;
- SARIF for Code Scanning interoperability.

SARIF may contain fewer results than the canonical finding set when safe source locations are unavailable.

## 10. Reproducibility

Record at minimum:

- repository/target revision;
- UAAF revision;
- CLI/configuration used;
- selected auditors;
- exclusions;
- output formats;
- validated environment when comparing results over time.

---
# End of Document
