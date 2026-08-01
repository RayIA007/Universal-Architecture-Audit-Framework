#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Architecture Audit Framework (UAAF) — Entry Point.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap: ensure 08_SCRIPTS is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
_SCRIPTS_DIR = _PROJECT_ROOT / "08_SCRIPTS"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from uaaf_core.cli import main

if __name__ == "__main__":
    sys.exit(main())