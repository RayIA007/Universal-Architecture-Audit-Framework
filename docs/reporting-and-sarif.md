# Reporting and SARIF

UAAF separates analysis from reporting. Auditor plugins produce canonical audit data; `ReportEngine` serializes that data into the requested public formats.

## Output formats

Supported formats:

```text
markdown
json
sarif
```

Historical/default formats:

```text
markdown,json
```

SARIF is opt-in.

```powershell
python run.py `
  --project-path . `
  --output-formats markdown,json,sarif
```

## Markdown

### What it is

The human-readable report format.

### What it contains

The Markdown renderer includes:

- UAAF audit header;
- plugin/audit identity;
- status;
- summary;
- metrics;
- findings grouped/presented by severity;
- execution metadata;
- execution errors when present.

### When to use it

Use Markdown for:

- human review;
- pull-request artifacts produced outside the canonical workflow;
- release/audit records;
- local inspection.

## JSON

### What it is

The machine-readable canonical UAAF result.

### When to use it

Use JSON when another script or system needs the complete UAAF data model rather than a SARIF projection.

Example:

```powershell
python run.py `
  --project-path . `
  --output-formats json
```

## Report paths and filenames

Without `--output-dir`, reports are written to:

```text
<UAAF_ROOT>/07_OUTPUTS
```

The report engine derives filenames from execution timing plus canonical plugin/audit identity and the selected extension.

A custom output directory can be supplied:

```powershell
python run.py `
  --project-path . `
  --output-dir reports
```

## SARIF 2.1.0

### What it is

UAAF's interoperability format for SARIF-compatible tooling, including GitHub Code Scanning.

The exporter emits:

```text
SARIF version: 2.1.0
Schema: SARIF 2.1.0 Errata 01
Tool name: UAAF
```

### Severity mapping

| UAAF severity | SARIF level |
|---|---|
| `critical` | `error` |
| `error` | `error` |
| `warning` | `warning` |
| `info` | `note` |

### Rules

UAAF findings are converted into SARIF rules and results. Rule construction is deduplicated and deterministic for the canonical input.

### Locations

UAAF only exports a SARIF source location when it can produce a safe project-relative artifact URI.

The exporter:

- normalizes exported artifact URIs to POSIX `/` separators;
- accepts safe project-relative paths;
- safely handles Windows-path input when it can be made project-relative;
- rejects paths escaping the audited project;
- avoids exporting unsafe drive/UNC/path forms;
- redacts absolute project-root text that appears in messages.

If a canonical finding has no safe exportable URI:

```text
finding remains in UAAF canonical data
finding remains in Markdown/JSON
finding is omitted from SARIF runs[].results[]
```

UAAF does this rather than inventing a source file.

### Source precision

UAAF exports a start line only when a valid positive source line exists.

It does not fabricate source coordinates to satisfy a SARIF consumer. The documented contract does not rely on invented columns, ranges, or fingerprints.

## Why SARIF can have fewer findings

Markdown/JSON represent the canonical UAAF audit data.

SARIF is an interoperability projection with stricter source-location requirements. Therefore:

```text
canonical finding count >= SARIF result count
```

can be a valid outcome.

This is not data loss from the canonical UAAF audit. It is a conservative export policy.

## GitHub Code Scanning

The repository's canonical workflow runs a controlled smoke audit and produces Markdown, JSON, and SARIF. It validates the SARIF file before upload.

The workflow then uses:

```text
github/codeql-action/upload-sarif@v4
```

with category:

```text
uaaf
```

### Permissions

The workflow is intentionally restricted:

```yaml
permissions:
  contents: read
```

The quality job additionally grants:

```yaml
permissions:
  contents: read
  security-events: write
```

to support SARIF upload.

### Fork protection

SARIF upload is skipped for pull requests whose head repository is a fork. The workflow does not use `pull_request_target`.

## CI-backed SARIF smoke execution

The canonical workflow audits:

```text
12_EXAMPLES/sample_project
```

with:

```text
configuration
```

and requests:

```text
markdown,json,sarif
```

It then checks:

- UAAF exit code is `0`;
- at least one Markdown report exists;
- at least one JSON report exists;
- exactly one SARIF report exists;
- SARIF version is `2.1.0`;
- one SARIF run exists;
- no absolute Windows path appears in the SARIF file.

## Practical examples

### Local SARIF generation

```powershell
python run.py `
  --project-path . `
  --auditors architecture `
  --output-formats sarif `
  --output-dir reports
```

### Keep human and machine reports together

```powershell
python run.py `
  --project-path . `
  --auditors all `
  --output-formats markdown,json,sarif `
  --output-dir reports
```

### CI quality gate plus SARIF

```powershell
python run.py `
  --project-path . `
  --auditors all `
  --output-formats markdown,json,sarif `
  --fail-on critical,error
```

A matching finding produces exit code `1`; an execution failure produces `2`.
