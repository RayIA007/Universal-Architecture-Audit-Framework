# UAAF Data Flow
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-ARC-008
**Version:** 1.0
**Status:** Maintained
**Classification:** Architecture
**Owner:** Architecture

---

## 1. Purpose

Describe how configuration, plugin data, findings, runtime state, and reports move through one current UAAF execution.

## 2. Input Flow

```text
CLI args -----------+
                    |
config file --------+--> configuration resolver --> ResolvedConfig
                    |
framework defaults -+
```

Explicit CLI values override ordinary file/default values.

Exclusions are merged.

## 3. Plugin Selection Flow

```text
ResolvedConfig
  -> UAAFRegistry.discover_plugins()
  -> validated PluginDescriptor objects
  -> selector resolution
  -> selected plugins
```

## 4. Plugin Context Flow

For each selected plugin:

```text
ResolvedConfig.plugin_defaults
  + plugin-specific configuration
  + project_path
  + audit_type
  + merged exclusions (when supported)
  -> isolated plugin context dictionary
```

Unsupported fields are rejected in canonical strict execution.

## 5. Runtime Flow

```text
selected PluginDescriptor
  + isolated context
  -> dynamic ProcessorContract adapter
  -> UAAFRuntime / RuntimePipeline
  -> descriptor.runner(plugin_context)
  -> AuditResult-compatible mapping
  -> runtime processor output
```

## 6. Consolidation Flow

```text
ordered plugin AuditResults
  -> validate
  -> collect findings/errors/metrics/status
  -> add source plugin traceability where needed
  -> consolidated AuditResult
```

## 7. Report Flow

```text
consolidated AuditResult
  -> ReportEngine
      -> Markdown
      -> JSON
      -> SarifExporter -> SARIF 2.1.0
```

Markdown/JSON preserve canonical audit information.

SARIF exports only findings that can be represented safely under SARIF location rules.

## 8. Exit-Code Flow

Exit code is computed from per-plugin execution status/errors and configured `fail_on` severities.

Report generation does not change finding severities.

## 9. Sensitive Data Flow

Diagnostic configuration snapshots are redacted by the configuration layer for sensitive key patterns.

SARIF path/message handling is conservative to avoid unsafe absolute project-path disclosure.

---
# End of Document
