"""
Smoke test for the UAAF Plugin Manager MVP.
"""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_FILE = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_FILE.parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "08_SCRIPTS"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from uaaf_core.plugins.plugin_manager import PluginManager


def main() -> int:
    manager = PluginManager(PROJECT_ROOT / "plugins")
    plugins = manager.discover()

    assert len(plugins) == 1, (
        f"Expected exactly one discovered plugin, found {len(plugins)}."
    )

    manifest = plugins[0]

    assert manifest.plugin_id == "documentation-auditor"
    assert manifest.name == "Documentation Auditor"
    assert manifest.version == "1.0.0"
    assert manifest.entrypoint == "plugin.py"

    registered = manager.get("documentation-auditor")
    assert registered == manifest

    print(manifest.plugin_id)
    print(manifest.name)
    print(manifest.version)
    print(manifest.entrypoint)
    print(len(plugins))
    print("[PASS] Plugin Manager smoke test completed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
