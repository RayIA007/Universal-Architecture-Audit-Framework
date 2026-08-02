"""
Configuration Auditor Plugin — Bootstrap
"""

from __future__ import annotations

import sys
from pathlib import Path

_PLUGIN_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _PLUGIN_FILE.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "08_SCRIPTS"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from plugins.configuration.configuration_auditor import (
    ConfigurationAuditorPlugin,
    run,
)

__all__ = [
    "ConfigurationAuditorPlugin",
    "run",
]