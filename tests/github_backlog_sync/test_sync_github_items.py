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

def test_apply_creates_then_reruns_skips_unchanged(tmp_path, templates_dir):
    _seed_epic(tmp_path, templates_dir)
    backend = FakeBackend()

    first = sync.apply_plan(sync.build_plan(sync.load_artifacts(tmp_path)), backend,
                            body_template=TEMPLATE, use_project=False)
    assert [r.action for r in first] == ["create"]
    assert len(backend.created) == 1

    # Re-load (frontmatter now has the number + a synced digest) and sync again. Nothing changed,
    # so it's a no-op skip — no duplicate issue, and no redundant update either.
    second = sync.apply_plan(sync.build_plan(sync.load_artifacts(tmp_path)), backend,
                             body_template=TEMPLATE, use_project=False)
    assert [r.action for r in second] == ["skip"]
    assert len(backend.created) == 1          # still just the one
    assert backend.updated == []              # unchanged content is not re-pushed


def test_synced_artifact_without_digest_is_an_update(tmp_path, templates_dir):
    # An artifact synced before digests existed (has github_issue but no github_synced_digest,
    # like a repo synced 'last week') can't be proven unchanged, so it updates rather than skips.
    art = _seed_epic(tmp_path, templates_dir)[0]
    sync.set_frontmatter_field(art.path, "github_issue", 31)
    plan = sync.build_plan(sync.load_artifacts(tmp_path))
    assert plan[0].action == "update"
    assert plan[0].changed is None
    assert plan[0].skip_unchanged is False


def test_edited_artifact_re_syncs_as_update(tmp_path, templates_dir):
    _seed_epic(tmp_path, templates_dir)
    backend = FakeBackend()
    sync.apply_plan(sync.build_plan(sync.load_artifacts(tmp_path)), backend,
                    body_template=TEMPLATE, use_project=False)
    # Edit the artifact body — its issue-shaping content now differs from the synced digest.
    art = sync.load_artifacts(tmp_path)[0]
    art.path.write_text(art.path.read_text(encoding="utf-8") + "\n\nNewly written detail.\n",
                        encoding="utf-8")
    result = sync.apply_plan(sync.build_plan(sync.load_artifacts(tmp_path)), backend,
                             body_template=TEMPLATE, use_project=False)
    assert [r.action for r in result] == ["update"]
    assert backend.updated  # the edited artifact was pushed


def test_stub_and_status_drift_flags(tmp_path, templates_dir):
    # A freshly scaffolded artifact still has <...> placeholder body -> stub.
    art = _seed_epic(tmp_path, templates_dir)[0]
    assert art.is_stub is True
    filled = sync.Artifact(path=art.path, type_key="epic", meta=art.meta,
                           body="Real, filled-in content with no placeholders.")
    assert filled.is_stub is False

    # A status off the canonical set is flagged as drift.
    sync.set_frontmatter_field(art.path, "status", "Backlogged")
    reloaded = sync.load_artifacts(tmp_path)[0]
    assert reloaded.status_is_canonical is False
    assert sync.build_plan([reloaded])[0].status_ok is False
    counts = sync.backlog_counts([reloaded])
    assert counts["stubs"] == 1 and counts["status_drift"] == 1


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
    # All three are freshly scaffolded stubs; statuses are canonical.
    assert counts == {"total": 3, "open": 2, "open_epics": 1, "stubs": 3, "status_drift": 0}


# --- rendering ----------------------------------------------------------------------------------

def test_render_issue_body_includes_backlink_and_id(tmp_path, templates_dir):
    art = _seed_epic(tmp_path, templates_dir)[0]
    body = sync.render_issue_body(art, TEMPLATE)
    assert art.id in body
    assert str(art.path) in body
