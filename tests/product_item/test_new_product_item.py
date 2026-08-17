"""Tests for the product-item scaffolder.

These pin the behaviour the v1/v2 merge had to preserve: YAML-safe titles (the
``#``/``:`` fix), the restored ``mkdir`` for a type's first artifact, the new
``--status`` / ``--standalone`` / ``--with-plan`` behaviour, gap-safe numbering,
and drift parity with the validator.
"""

from __future__ import annotations

import new_product_item as npi
import pytest
import validate_product_items as vpi


# --- YAML-safe titles (the "PR #30" regression) --------------------------------

def test_yaml_title_plain_passthrough():
    assert npi.yaml_title("Payments platform") == "Payments platform"


def test_yaml_title_quotes_hash():
    # A '#' must not be treated as a YAML comment and truncate the title.
    assert npi.yaml_title("Handle PR #30 titles") == '"Handle PR #30 titles"'


def test_yaml_title_quotes_colon():
    assert npi.yaml_title("Feature: sync to GitHub") == '"Feature: sync to GitHub"'


def test_yaml_title_escapes_embedded_quotes():
    assert npi.yaml_title('a "quoted" #ref') == '"a \\"quoted\\" #ref"'


def test_slugify_drops_hash_and_punctuation():
    assert npi.slugify("Handle PR #30 titles!") == "handle-pr-30-titles"


# --- gap-safe numbering --------------------------------------------------------

def test_next_id_is_gap_safe(tmp_path):
    epics = tmp_path / "epics"
    epics.mkdir()
    (epics / "EPIC-001-a.md").write_text("x", encoding="utf-8")
    (epics / "EPIC-003-c.md").write_text("x", encoding="utf-8")
    assert npi.next_id(tmp_path, "epic") == "004"  # never reuses the 002 gap


def test_next_id_empty_dir_starts_at_001(tmp_path):
    assert npi.next_id(tmp_path, "task") == "001"


def test_next_id_counts_archived_ids(tmp_path):
    # An archived EPIC-002 must still count, so the next id is 003 — never a
    # reused 002. Proves next_id recurses into <type>/archive/.
    epics = tmp_path / "epics"
    (epics).mkdir()
    (epics / "EPIC-001-active.md").write_text("x", encoding="utf-8")
    archive = epics / "archive"
    archive.mkdir()
    (archive / "EPIC-002-shipped.md").write_text("x", encoding="utf-8")
    assert npi.next_id(tmp_path, "epic") == "003"


# --- create(): the restored mkdir + new flags ----------------------------------

def test_create_makes_missing_type_dir(tmp_path, templates_dir):
    # The regression the merge restored: the first artifact of a type must
    # create docs/product/<type>/ rather than failing on a missing dir.
    dest = npi.create(
        "epic", "Payments platform",
        product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29",
    )
    assert dest.exists()
    assert dest.parent.name == "epics"


def test_create_refuses_overwrite(tmp_path, templates_dir, monkeypatch):
    # Pin the id so the second create targets the same path (next_id is
    # otherwise gap-safe and wouldn't collide).
    monkeypatch.setattr(npi, "next_id", lambda *a, **k: "001")
    npi.create("epic", "Fixed", product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29")
    with pytest.raises(FileExistsError):
        npi.create("epic", "Fixed", product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29")


def test_create_stamps_status(tmp_path, templates_dir):
    dest = npi.create(
        "task", "Do the thing",
        product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29",
        status="In Progress",
    )
    assert "status: In Progress" in dest.read_text(encoding="utf-8")


def test_create_standalone_nulls_parent(tmp_path, templates_dir):
    dest = npi.create(
        "task", "Orphan chore",
        product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29",
        standalone=True,
    )
    assert "story: none" in dest.read_text(encoding="utf-8")


def test_create_quotes_hash_title_in_frontmatter(tmp_path, templates_dir):
    dest = npi.create(
        "task", "Handle PR #30 titles",
        product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29",
    )
    assert 'title: "Handle PR #30 titles"' in dest.read_text(encoding="utf-8")


# --- create_with_plan(): cross-wiring ------------------------------------------

def test_create_with_plan_cross_wires_task_and_plan(tmp_path, templates_dir):
    item, plan = npi.create_with_plan(
        "task", "Wire webhook retries",
        product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29",
    )
    assert "plan: PLAN-001" in item.read_text(encoding="utf-8")
    assert "covers: TASK-001" in plan.read_text(encoding="utf-8")


def test_create_with_plan_rejects_plan_type(tmp_path, templates_dir):
    with pytest.raises(ValueError):
        npi.create_with_plan(
            "plan", "nope",
            product_dir=tmp_path, templates_dir=templates_dir, today="2026-07-29",
        )


# --- drift guards: scaffolder <-> validator ------------------------------------

def test_status_set_matches_validator():
    assert npi.VALID_STATUSES == vpi.VALID_STATUSES


def test_type_map_matches_validator():
    scaffolder = {k: (s.directory, s.prefix) for k, s in npi.TYPE_SPEC.items()}
    gate = {k: (t.directory, t.prefix) for k, t in vpi._TYPES.items()}
    assert scaffolder == gate
