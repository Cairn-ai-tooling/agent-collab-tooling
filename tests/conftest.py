"""Shared pytest fixtures/paths for the bundled-script tests.

The product-item scripts ship as skill *assets* (copied into consuming repos),
not as an installed package, so they aren't on the default import path. Put
their directory on ``sys.path`` here so tests can ``import new_product_item`` /
``import validate_product_items`` by module name.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
_PRODUCT_ITEM = REPO_ROOT / "skills" / "product-item" / "assets"
SCRIPTS_DIR = _PRODUCT_ITEM / "scripts"
TEMPLATES_DIR = _PRODUCT_ITEM / "templates"

sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def templates_dir() -> Path:
    """The real product-item templates, so tests exercise the shipped scaffolds."""
    return TEMPLATES_DIR
