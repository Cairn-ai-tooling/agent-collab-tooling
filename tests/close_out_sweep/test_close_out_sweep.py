"""Tests for the close-out-sweep engine.

The plan builder is pure (reads the backlog, resolves each Done epic's subtree via frontmatter
links). Apply drives ``git mv`` + regenerates the shipped index + prunes the roadmap, so its test
runs in a real throwaway git repo. Idempotence: once archived, a re-run finds nothing to sweep.
"""

from __future__ import annotations

import subprocess

import close_out_sweep as cos
import new_product_item as npi


def _mark_done(path):
    path.write_text(path.read_text(encoding="utf-8").replace("status: Proposed", "status: Done"),
                    encoding="utf-8")


def _backlog(tmp_path, templates_dir):
    """An epic with a story, a task, and a plan — linked into one subtree."""
    product = tmp_path / "docs" / "product"
    epic = npi.create("epic", "Search overhaul", product_dir=product, templates_dir=templates_dir,
                      today="2026-07-29", roadmap_ref="R1")
    story = npi.create("story", "Faceted filters", product_dir=product, templates_dir=templates_dir,
                       today="2026-07-29", parent="EPIC-001")
    task = npi.create("task", "Index the catalogue", product_dir=product, templates_dir=templates_dir,
                      today="2026-07-29", parent="STORY-001")
    plan = npi.create("plan", "Ship search", product_dir=product, templates_dir=templates_dir,
                      today="2026-07-29", covers="TASK-001")
    return product, [epic, story, task, plan]


def test_proposed_epic_is_not_swept(tmp_path, templates_dir):
    product, _ = _backlog(tmp_path, templates_dir)
    assert cos.build_plan(product) == []  # nothing Done -> no-op


def test_build_plan_resolves_the_done_epic_subtree(tmp_path, templates_dir):
    product, files = _backlog(tmp_path, templates_dir)
    for f in files:
        _mark_done(f)
    plan = cos.build_plan(product)
    assert len(plan) == 1
    assert sorted(m.id for m in plan[0].files) == ["EPIC-001", "PLAN-001", "STORY-001", "TASK-001"]
    assert plan[0].not_done == []


def test_not_done_subtree_member_is_flagged(tmp_path, templates_dir):
    product, files = _backlog(tmp_path, templates_dir)
    epic, story, task, plan = files
    _mark_done(epic)
    _mark_done(story)
    _mark_done(plan)  # leave the task Proposed
    result = cos.build_plan(product)
    assert result[0].not_done == ["TASK-001"]


def test_apply_archives_regenerates_and_is_idempotent(tmp_path, templates_dir):
    product, files = _backlog(tmp_path, templates_dir)
    for f in files:
        _mark_done(f)
    roadmap = tmp_path / "docs" / "roadmap.md"
    roadmap.write_text("# Roadmap\n\n- **R1** Search overhaul → `EPIC-001`\n- **R2** Something else\n",
                       encoding="utf-8")
    # git repo so `git mv` works
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], check=True)

    summary = cos.apply_plan(cos.build_plan(product), product)
    assert summary["epics"] == 1
    assert summary["files_moved"] == 4

    # whole subtree moved into per-type archive/ dirs
    assert (product / "epics" / "archive" / "EPIC-001-search-overhaul.md").exists()
    assert (product / "stories" / "archive" / "STORY-001-faceted-filters.md").exists()
    assert (product / "tasks" / "archive" / "TASK-001-index-the-catalogue.md").exists()
    assert (product / "implementation-plans" / "archive" / "PLAN-001-ship-search.md").exists()

    # shipped index regenerated from the now-archived Done epic
    shipped = (product / "shipped.md").read_text(encoding="utf-8")
    assert "[EPIC-001](epics/archive/EPIC-001-search-overhaul.md)" in shipped
    assert "| R1 |" in shipped

    # roadmap row for the shipped epic pruned; the unrelated row stays
    roadmap_text = roadmap.read_text(encoding="utf-8")
    assert "EPIC-001" not in roadmap_text
    assert "R2" in roadmap_text

    # idempotent: the epic is archived now, so a re-run has nothing to sweep
    assert cos.build_plan(product) == []
