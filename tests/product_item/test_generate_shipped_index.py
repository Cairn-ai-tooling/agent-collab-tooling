"""Tests for the shipped-index generator.

It derives docs/product/shipped.md from `Done` epics only (recursing epics/archive/), sorted by
id, with an empty-state placeholder — never hand-maintained.
"""

from __future__ import annotations

import generate_shipped_index as gsi
import new_product_item as npi


def _archived_done_epic(tmp_path, templates_dir, title, *, roadmap):
    """Create an epic, mark it Done, and move it into epics/archive/."""
    epic = npi.create("epic", title, product_dir=tmp_path, templates_dir=templates_dir,
                      today="2026-07-29", roadmap_ref=roadmap)
    epic.write_text(epic.read_text(encoding="utf-8").replace("status: Proposed", "status: Done"),
                    encoding="utf-8")
    archive = tmp_path / "epics" / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    return epic.rename(archive / epic.name)


def test_collect_only_done_epics_sorted(tmp_path, templates_dir):
    # A Proposed active epic (EPIC-001, excluded) + two Done archived epics.
    npi.create("epic", "Active WIP", product_dir=tmp_path, templates_dir=templates_dir,
               today="2026-07-29")
    _archived_done_epic(tmp_path, templates_dir, "Toggl", roadmap="R1")          # EPIC-002
    _archived_done_epic(tmp_path, templates_dir, "DST guardrail", roadmap="R17")  # EPIC-003

    rows = gsi.collect_shipped(tmp_path)
    assert [r["id"] for r in rows] == ["EPIC-002", "EPIC-003"]  # Done only, sorted; WIP excluded
    assert rows[0]["roadmap_ref"] == "R1"
    assert rows[0]["relpath"] == "epics/archive/EPIC-002-toggl.md"


def test_main_writes_index_row(tmp_path, templates_dir):
    _archived_done_epic(tmp_path, templates_dir, "Toggl", roadmap="R1")  # EPIC-001
    gsi.main([str(tmp_path)])
    shipped = (tmp_path / "shipped.md").read_text(encoding="utf-8")
    assert "| R1 | [EPIC-001](epics/archive/EPIC-001-toggl.md) | Toggl |" in shipped


def test_empty_state_when_nothing_shipped(tmp_path, templates_dir):
    npi.create("epic", "Still in flight", product_dir=tmp_path, templates_dir=templates_dir,
               today="2026-07-29")  # Proposed, not Done
    gsi.main([str(tmp_path)])
    assert "_(none yet)_" in (tmp_path / "shipped.md").read_text(encoding="utf-8")
