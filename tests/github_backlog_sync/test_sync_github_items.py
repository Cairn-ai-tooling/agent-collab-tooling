"""Tests for the github-backlog-sync engine.

The engine (load → plan → apply → frontmatter write-back) talks to an ``IssueBackend``, so a
fake backend exercises the whole flow with no network. These pin the properties that matter:
create-vs-update decisions, idempotency (a re-run updates instead of duplicating), status→state
mapping, project write-back, and the targeted frontmatter edit.
"""

from __future__ import annotations

import new_product_item as npi
import pytest
import sync_github_items as sync


# --- a fake backend that records calls and hands out issue numbers -----------------------------

class FakeBackend(sync.IssueBackend):
    def __init__(self):
        self.created = []      # list[(title, label)]
        self.updated = []      # list[(number, title)]
        self.states = {}       # number -> is_open
        self.project_items = {}  # number -> item_id
        self.project_status = {}  # item_id -> status
        self._next = 100

    def create_issue(self, *, title, body, label):
        self._next += 1
        self.created.append((title, label))
        return self._next

    def update_issue(self, number, *, title, body, label):
        self.updated.append((number, title))

    def set_issue_state(self, number, *, is_open):
        self.states[number] = is_open

    def add_to_project(self, number):
        item_id = f"PVTI_{number}"
        self.project_items[number] = item_id
        return item_id

    def set_project_status(self, item_id, *, status):
        self.project_status[item_id] = status


TEMPLATE = "**{type} {status}** {id} @ {artifact_path}\n{parent}\n{body}"


def _seed_epic(tmp_path, templates_dir, **kwargs):
    npi.create("epic", kwargs.pop("title", "Payments"), product_dir=tmp_path,
               templates_dir=templates_dir, today="2026-07-29", **kwargs)
    return sync.load_artifacts(tmp_path)


# --- plan ---------------------------------------------------------------------------------------

def test_build_plan_marks_new_artifact_as_create(tmp_path, templates_dir):
    plan = sync.build_plan(_seed_epic(tmp_path, templates_dir))
    assert [p.action for p in plan] == ["create"]
    assert plan[0].title.startswith("EPIC-001 ")
    assert plan[0].label == "epic"


def test_build_plan_marks_synced_artifact_as_update(tmp_path, templates_dir):
    _seed_epic(tmp_path, templates_dir)
    art = sync.load_artifacts(tmp_path)[0]
    sync.set_frontmatter_field(art.path, "github_issue", 42)
    plan = sync.build_plan(sync.load_artifacts(tmp_path))
    assert plan[0].action == "update"
    assert plan[0].artifact.github_issue == 42


def test_done_status_plans_a_closed_issue(tmp_path, templates_dir):
    npi.create("task", "Finished", product_dir=tmp_path, templates_dir=templates_dir,
               today="2026-07-29", status="Done")
    plan = sync.build_plan(sync.load_artifacts(tmp_path))
    assert plan[0].is_open is False


# --- frontmatter write-back ---------------------------------------------------------------------

def test_set_frontmatter_field_inserts_then_replaces(tmp_path, templates_dir):
    art = _seed_epic(tmp_path, templates_dir)[0]
    sync.set_frontmatter_field(art.path, "github_issue", 7)
    assert sync.load_artifacts(tmp_path)[0].github_issue == 7
    # Replacing keeps a single line, not a duplicate.
    sync.set_frontmatter_field(art.path, "github_issue", 8)
    text = art.path.read_text(encoding="utf-8")
    assert text.count("github_issue:") == 1
    assert sync.load_artifacts(tmp_path)[0].github_issue == 8


# --- apply + idempotency ------------------------------------------------------------------------

def test_apply_creates_then_reruns_as_update(tmp_path, templates_dir):
    _seed_epic(tmp_path, templates_dir)
    backend = FakeBackend()

    first = sync.apply_plan(sync.build_plan(sync.load_artifacts(tmp_path)), backend,
                            body_template=TEMPLATE, use_project=False)
    assert [r.action for r in first] == ["create"]
    assert len(backend.created) == 1

    # Re-load (frontmatter now has the number) and sync again: update, no new issue.
    second = sync.apply_plan(sync.build_plan(sync.load_artifacts(tmp_path)), backend,
                             body_template=TEMPLATE, use_project=False)
    assert [r.action for r in second] == ["update"]
    assert len(backend.created) == 1          # still just the one
    assert backend.updated and backend.updated[0][0] == first[0].number


def test_apply_sets_state_from_status(tmp_path, templates_dir):
    npi.create("task", "Wrap up", product_dir=tmp_path, templates_dir=templates_dir,
               today="2026-07-29", status="Archived")
    backend = FakeBackend()
    results = sync.apply_plan(sync.build_plan(sync.load_artifacts(tmp_path)), backend,
                              body_template=TEMPLATE, use_project=False)
    assert backend.states[results[0].number] is False   # Archived -> closed


def test_apply_with_project_writes_back_item_and_status(tmp_path, templates_dir):
    npi.create("story", "Checkout", product_dir=tmp_path, templates_dir=templates_dir,
               today="2026-07-29", status="In Progress")
    backend = FakeBackend()
    results = sync.apply_plan(sync.build_plan(sync.load_artifacts(tmp_path)), backend,
                              body_template=TEMPLATE, use_project=True)
    number = results[0].number
    item_id = backend.project_items[number]
    assert backend.project_status[item_id] == "In Progress"
    # The item id was written back, so a re-run reuses it instead of re-adding.
    reloaded = sync.load_artifacts(tmp_path)[0]
    assert reloaded.meta.get("github_project_item") == item_id


# --- counts / metric ----------------------------------------------------------------------------

def test_backlog_counts(tmp_path, templates_dir):
    npi.create("epic", "E1", product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29")
    npi.create("epic", "E2", product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29",
               status="Done")
    npi.create("task", "T1", product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29")
    counts = sync.backlog_counts(sync.load_artifacts(tmp_path))
    assert counts == {"total": 3, "open": 2, "open_epics": 1}


# --- rendering ----------------------------------------------------------------------------------

def test_render_issue_body_includes_backlink_and_id(tmp_path, templates_dir):
    art = _seed_epic(tmp_path, templates_dir)[0]
    body = sync.render_issue_body(art, TEMPLATE)
    assert art.id in body
    assert str(art.path) in body
