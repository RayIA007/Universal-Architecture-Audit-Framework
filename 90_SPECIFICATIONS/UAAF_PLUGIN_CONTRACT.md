# UAAF Plugin Contract
**Universal Architecture Audit Framework v1.0**

**Document ID:** UAAF-CTR-002
**Version:** 1.0
**Status:** Approved
**Classification:** Contract

---

# 1. Purpose

This document defines the mandatory contract for every UAAF plugin.

A plugin extends framework capabilities without modifying the Kernel.

---

# 2. Scope

This contract applies to every official and third-party plugin.

---

# 3. Plugin Principles

Every plugin shall:

- Have one primary responsibility.
- Be independently deployable.
- Be independently testable.
- Be discoverable by the Registry.
- Be versioned.
- Respect Kernel contracts.

---

# 4. Mandatory Metadata

Every plugin shall declare:

- Plugin Identifier
- Name
- Version
- Author
- Description
- Compatibility
- Supported Profiles

---

# 5. Registration

Every plugin shall register itself before execution.

Unregistered plugins shall not participate in an audit.

---

# 6. Lifecycle

Every plugin shall support the following lifecycle:

1. Registration
2. Validation
3. Initialization
4. Execution
5. Finalization
6. Disposal

---

# 7. Responsibilities

A plugin may provide one or more of the following:

- Processor
- Rule Package
- Audit Profile
- Report Template
- Validator
- Adapter

---

# 8. Restrictions

A plugin shall never:

- Modify Kernel behavior.
- Modify another plugin.
- Bypass contracts.
- Alter audit evidence.
- Circumvent traceability.

---

# 9. Compatibility

Plugins shall declare the supported UAAF version.

Incompatible plugins shall not be loaded.

---

# 10. Compliance

A plugin is considered compliant when it satisfies this contract and all mandatory validation rules.

---

# End of Document