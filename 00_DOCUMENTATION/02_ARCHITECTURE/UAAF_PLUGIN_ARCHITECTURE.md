# UAAF Plugin Architecture
**Universal Architecture Audit Framework (UAAF)**

**Document ID:** UAAF-ARC-005
**Version:** 1.0
**Status:** Maintained
**Classification:** Architecture
**Owner:** Architecture

---

## 1. Purpose

Define the current auditor plugin model used by UAAF.

## 2. Canonical Public Runner

Every discovered auditor exposes:

```python
run(context) -> dict[str, Any]
```

The returned mapping must satisfy the canonical `AuditResult` contract.

Some plugin packages also expose an `execute()` wrapper for compatibility or direct use, but unified orchestration depends on the validated runner contract.

## 3. PluginDescriptor

The registry represents a validated plugin with an immutable `PluginDescriptor` carrying:

- name;
- audit type;
- plugin ID;
- plugin version;
- package/module paths;
- callable runner;
- imported module;
- allowed context fields;
- deterministic/stable path metadata;
- additional validated metadata;
- validation status.

## 4. Discovery

The canonical plugin directory is:

```text
<UAAF_ROOT>/plugins
```

Current discovered plugin packages:

```text
architecture
documentation
testing
configuration
ai_systems
```

The registry validates candidate structure, importability, required metadata, uniqueness, aliases, and callable runner behavior.

## 5. Selection

Stable public selectors include audit types and canonical plugin IDs.

```text
architecture      -> architecture-auditor
documentation     -> documentation-auditor
testing           -> testing-auditor
configuration     -> configuration-auditor
ai_systems        -> ai-systems-auditor
```

Discovery and selection order are deterministic.

## 6. Configuration Isolation

Global plugin defaults and plugin-specific sections are resolved before execution.

Only fields declared/supported by the target plugin are projected in strict canonical execution.

Reserved fields cannot be overridden by plugin-specific configuration.

## 7. Runtime Adaptation

The unified orchestrator adapts each selected plugin to a runtime `ProcessorContract`.

This adapter calls the plugin runner and stores canonical audit output without requiring the plugin itself to implement the lower-level runtime processor class.

## 8. Failure Isolation

An unexpected plugin exception is converted into a failed canonical audit result so that failure information is preserved consistently.

Final execution semantics still return process exit code `2` when a selected plugin has execution errors or failure status.

## 9. Adding a Plugin

A new plugin must:

1. live in a discoverable plugin package;
2. expose required metadata used by the registry;
3. expose callable `run(context)`;
4. return canonical `AuditResult`-compatible data;
5. document supported configuration fields;
6. include deterministic tests;
7. avoid modifying core orchestration for auditor-specific rule logic.

## 10. Current Boundary

The plugin system executes trusted Python code. It is not a sandbox for untrusted third-party plugins.

---
# End of Document
