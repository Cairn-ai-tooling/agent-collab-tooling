"""Shared pytest fixtures/paths for the bundled-script tests.

Skills' Python scripts ship as *assets* (copied into consuming repos), not as an
installed package, so they aren't on the default import path. Put every skill's
``scripts/`` dir on ``sys.path`` here so tests can import them by module name
(e.g. ``import new_product_item`` / ``import close_out_sweep``, ``import sync_github_items``), and so a script
that reuses a sibling (the sweep imports product-item's generator) resolves too.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
TEMPLATES_DIR = SKILLS_DIR / "product-item" / "assets" / "templates"

for _scripts in sorted(SKILLS_DIR.glob("*/assets/scripts")):
    sys.path.insert(0, str(_scripts))


@pytest.fixture
def templates_dir() -> Path:
    """The real product-item templates, so tests exercise the shipped scaffolds."""
    return TEMPLATES_DIR
