"""
Version information for the UAAF Patch Engine.

This module is intentionally independent from the rest of the component so
the Patch Engine version can be inspected without initializing the execution
engine or importing implementation modules.
"""

from __future__ import annotations


VERSION_MAJOR = 0
VERSION_MINOR = 1
VERSION_PATCH = 0
VERSION_STAGE = "alpha"

VERSION_INFO = (
    VERSION_MAJOR,
    VERSION_MINOR,
    VERSION_PATCH,
    VERSION_STAGE,
)

__version__ = (
    f"{VERSION_MAJOR}."
    f"{VERSION_MINOR}."
    f"{VERSION_PATCH}-"
    f"{VERSION_STAGE}"
)

PATCH_ENGINE_NAME = "UAAF Patch Engine"


__all__ = [
    "PATCH_ENGINE_NAME",
    "VERSION_INFO",
    "VERSION_MAJOR",
    "VERSION_MINOR",
    "VERSION_PATCH",
    "VERSION_STAGE",
    "__version__",
]