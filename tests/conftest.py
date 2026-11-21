"""Load the Home Assistant independent modules without importing the package.

``custom_components/iwona_pellets/__init__.py`` imports Home Assistant, which is
not needed (nor installed) to test the protocol and register decoding.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PKG = Path(__file__).parent.parent / "custom_components" / "iwona_pellets"


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"iwona_{name}", PKG / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))
