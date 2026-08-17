"""Batch close-out: archive every completed Epic's subtree and regenerate the shipped index.

Why this script exists
======================

When Epics ship, they graduate *out* of the active ``docs/product/`` backlog into per-type
``archive/`` dirs (see the ``close-out-sweep`` skill and ``docs/product/README.md``). Doing that
epic-by-epic is tedious and easy to get wrong — you have to find each Epic's whole subtree
(its stories, tasks, and plan) via the frontmatter links and move them together so no
active→archived dangling link is created. This script makes the sweep **deterministic and
idempotent**:

- It finds every **active** Epic whose ``status`` is ``Done`` (already-archived ones are skipped,
  so a re-run with nothing new to close is a no-op).
- It resolves each Done Epic's **whole subtree** via frontmatter links (stories → tasks → plans)
  and moves the unit together with ``git mv`` — epic-granular, so links stay cohesive.
- It regenerates ``docs/product/shipped.md`` by **reusing product-item's**
  ``generate_shipped_index.py`` (not a duplicate), and removes the shipped Epics' rows from
  ``docs/roadmap.md`` (outstanding-only; the CHANGELOG keeps the narrative).

It is **plan-only by default**; the ``git mv`` / edits happen only under ``--apply``. Committing is
left to the user. Self-contained except for ``git`` and product-item's generator. Modelled on the
``github-backlog-sync`` sync engine: load → plan → apply.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DIR = REPO_ROOT / "docs" / "product"

# Artifact type -> its active directory. Parallel to product-item's TYPE_SPEC.
TYPE_DIRS: dict[str, str] = {
    "epic": "epics",
    "story": "stories",
    "task": "tasks",
    "plan": "implementation-plans",
}


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Return the YAML frontmatter mapping, or ``{}`` if absent/malformed."""
    if not text.startswith("---"):
        return {}
    parts = text.split("\n---", 1)
    if len(parts) != 2:
        return {}
    try:
        meta = yaml.safe_load(parts[0][len("---"):])
    except yaml.YAMLError:
        return {}
    return meta if isinstance(meta, dict) else {}


@dataclass
class Artifact:
    path: Path
    type_key: str
    meta: dict[str, Any]

    @property
    def id(self) -> str:
        return str(self.meta.get("id", ""))

    @property
    def status(self) -> str:
        return str(self.meta.get("status", ""))


def _is_archived(path: Path, product_dir: Path) -> bool:
    return "archive" in path.relative_to(product_dir).parts


def load_active(product_dir: Path) -> list[Artifact]:
    """Load every **active** (non-archived) artifact with well-formed frontmatter."""
    out: list[Artifact] = []
    for type_key, directory in TYPE_DIRS.items():
        d = product_dir / directory
        if not d.is_dir():
            continue
        for path in sorted(d.rglob("*.md")):
            if _is_archived(path, product_dir):
                continue
            meta = parse_frontmatter(path.read_text(encoding="utf-8"))
            if meta:
                out.append(Artifact(path=path, type_key=type_key, meta=meta))
    return out


@dataclass
class EpicPlan:
    epic: Artifact
    files: list[Artifact]          # the epic + its whole active subtree, to archive together
    not_done: list[str] = field(default_factory=list)  # subtree member ids that aren't Done (warn)

    @property
    def epic_id(self) -> str:
        return self.epic.id


def _subtree(epic: Artifact, actives: list[Artifact]) -> list[Artifact]:
    """The epic plus its stories, their tasks, and any plans covering the epic/stories/tasks —
    resolved through frontmatter links, over the active artifacts only."""
    by_type: dict[str, list[Artifact]] = {t: [] for t in TYPE_DIRS}
    for a in actives:
        by_type[a.type_key].append(a)

    members: list[Artifact] = [epic]
    stories = [s for s in by_type["story"] if s.meta.get("epic") == epic.id]
    members += stories
    story_ids = {s.id for s in stories}
    tasks = [t for t in by_type["task"] if t.meta.get("story") in story_ids]
    members += tasks

    covered = {epic.id} | story_ids | {t.id for t in tasks}
    plans = [p for p in by_type["plan"] if p.meta.get("covers") in covered]
    members += plans
    return members


def build_plan(product_dir: Path) -> list[EpicPlan]:
    """One EpicPlan per active Done epic — the subtree it would archive. Pure (read-only)."""
    actives = load_active(product_dir)
    plans: list[EpicPlan] = []
    for epic in [a for a in actives if a.type_key == "epic" and a.status == "Done"]:
        members = _subtree(epic, actives)
        not_done = [m.id for m in members if m.status != "Done"]
        plans.append(EpicPlan(epic=epic, files=members, not_done=not_done))
    return plans


# --------------------------------------------------------------------------------------------
# git + apply
# --------------------------------------------------------------------------------------------

def _git(args: list[str], cwd: Path) -> None:
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")


def _regenerate_shipped_index(product_dir: Path) -> None:
    """Reuse product-item's generator rather than duplicating it. At runtime it sits next to this
    script (both bootstrapped into the repo's ``scripts/``); in tests the product-item scripts dir
    is on ``sys.path``. Imported lazily so a missing generator is a clear, actionable error."""
    try:
        import generate_shipped_index
    except ImportError as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            "generate_shipped_index.py not found alongside this script — it is provided by the "
            "product-item skill; bootstrap product-item into this repo first."
        ) from exc
    generate_shipped_index.main([str(product_dir)])


def _remove_roadmap_rows(roadmap_path: Path, epic_ids: set[str]) -> int:
    """Drop any roadmap line that references a shipped epic id (the ``→ EPIC-NNN`` pointer that
    product-item appends). Returns the number of lines removed. No-op if the file is absent."""
    if not roadmap_path.is_file():
        return 0
    lines = roadmap_path.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [ln for ln in lines if not any(eid in ln for eid in epic_ids)]
    removed = len(lines) - len(kept)
    if removed:
        roadmap_path.write_text("".join(kept), encoding="utf-8")
    return removed


def apply_plan(plan: list[EpicPlan], product_dir: Path) -> dict[str, int]:
    """Archive each planned subtree with ``git mv``, regenerate the shipped index, and prune the
    roadmap. Returns a small summary. Does not commit — that's left to the user."""
    moved = 0
    for item in plan:
        for member in item.files:
            archive_dir = product_dir / TYPE_DIRS[member.type_key] / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            _git(["mv", str(member.path), str(archive_dir / member.path.name)], product_dir)
            moved += 1

    epic_ids = {item.epic_id for item in plan}
    roadmap_removed = _remove_roadmap_rows(product_dir.parent / "roadmap.md", epic_ids) if plan else 0
    if plan:
        _regenerate_shipped_index(product_dir)
    return {"epics": len(plan), "files_moved": moved, "roadmap_rows_removed": roadmap_removed}


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------

def _print_plan(plan: list[EpicPlan]) -> None:
    if not plan:
        print("No active Done epics to close out — nothing to sweep.")
        return
    total = sum(len(p.files) for p in plan)
    print(f"Close-out plan: {len(plan)} epic(s), {total} file(s) to archive.\n")
    for item in plan:
        print(f"  {item.epic_id} — {item.epic.meta.get('title', '')}  ({len(item.files)} files)")
        for member in item.files:
            print(f"      archive: {member.path.name}")
        if item.not_done:
            print(f"      ! not yet Done (mark the whole subtree Done first): {', '.join(item.not_done)}")
    print("\n(dry-run — nothing moved. Re-run with --apply to archive + regenerate shipped.md.)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Archive every completed Epic's subtree and regenerate the shipped index."
    )
    parser.add_argument("product_dir", nargs="?", default=str(PRODUCT_DIR),
                        help="path to the product backlog (default: docs/product)")
    parser.add_argument("--apply", action="store_true",
                        help="actually git mv + regenerate (default: plan only)")
    args = parser.parse_args(argv)

    # Resolve to an absolute path: apply runs git with ``-C product_dir`` and passes the artifact
    # paths through, so a relative product_dir would otherwise be doubled up under it.
    product_dir = Path(args.product_dir).resolve()
    if not product_dir.is_dir():
        print(f"error: not a directory: {product_dir}", file=sys.stderr)
        return 2

    plan = build_plan(product_dir)

    if not args.apply:
        _print_plan(plan)
        return 0

    if not plan:
        print("No active Done epics to close out — nothing to sweep.")
        return 0

    summary = apply_plan(plan, product_dir)
    print(f"Closed out {summary['epics']} epic(s): moved {summary['files_moved']} file(s) to "
          f"archive/, removed {summary['roadmap_rows_removed']} roadmap row(s), regenerated "
          f"shipped.md. Review with `git status` and commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
