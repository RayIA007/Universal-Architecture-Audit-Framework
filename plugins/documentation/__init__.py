"""
Documentation Auditor Plugin — Bootstrap and exports.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap: ensure 08_SCRIPTS is on sys.path so uaaf_core is importable
_PLUGIN_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _PLUGIN_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "08_SCRIPTS"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from .documentation_auditor import DocumentationAuditorPlugin, run

__all__ = [
    "DocumentationAuditorPlugin",
    "run",
]