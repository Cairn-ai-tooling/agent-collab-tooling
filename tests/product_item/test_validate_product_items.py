"""Tests for the product-item integrity gate.

Confirm it stays self-contained (imports only stdlib + pyyaml, no application
package), passes on freshly-scaffolded artifacts, and catches the drift it is
meant to catch: duplicate ids, dangling links, and invalid statuses.
"""

from __future__ import annotations

import new_product_item as npi
import validate_product_items as vpi


def _messages(product_dir):
    return [v.message for v in vpi.validate_tree(product_dir)]


def test_clean_tree_has_no_violations(tmp_path, templates_dir):
    npi.create("epic", "An epic", product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29")
    assert vpi.validate_tree(tmp_path) == []


def test_freshly_scaffolded_artifact_is_tolerated(tmp_path, templates_dir):
    # A Proposed story keeps its `epic: EPIC-NNN` placeholder — the lenient gate
    # must not flag unfilled scaffold placeholders.
    npi.create("story", "A story", product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29")
    assert vpi.validate_tree(tmp_path) == []


def test_duplicate_id_detected(tmp_path, templates_dir):
    first = npi.create("epic", "Alpha", product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29")
    (tmp_path / "epics" / "EPIC-001-copy.md").write_text(first.read_text(encoding="utf-8"), encoding="utf-8")
    assert any("duplicate id EPIC-001" in m for m in _messages(tmp_path))


def test_dangling_link_detected(tmp_path, templates_dir):
    npi.create(
        "task", "Task with bad parent",
        product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29",
        parent="STORY-999",
    )
    assert any("STORY-999" in m and "does not resolve" in m for m in _messages(tmp_path))


def test_invalid_status_detected(tmp_path, templates_dir):
    dest = npi.create("epic", "Beta", product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29")
    dest.write_text(
        dest.read_text(encoding="utf-8").replace("status: Proposed", "status: Bogus"),
        encoding="utf-8",
    )
    assert any("invalid status" in m for m in _messages(tmp_path))
