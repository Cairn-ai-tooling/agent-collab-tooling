"""Scaffold a product-management artifact (Epic / User Story / Task / Plan).

Why this script exists
======================

The product-management workflow (see ``docs/product/README.md``) tracks work as
numbered artifacts — ``EPIC-001``, ``STORY-001``, ``TASK-001``, ``PLAN-001`` —
each created from a template in ``docs/product/templates/`` with YAML
frontmatter that has to stay accurate for the repository to be navigable.

Doing that by hand is error-prone: you must find the highest existing number
for the type, zero-pad it, copy the right template, and fill the id / date /
parent fields consistently. This script makes the *deterministic* part
mechanical and idempotent so the ``/product-item`` skill can focus on the
judgement (which type, title, which parent to wire up).

It deliberately does **one** thing: create and fill a single new artifact file,
then print its path. Wiring the new child into its parent document and adding a
roadmap pointer are "with-confirm" edits left to the skill, keeping this
script's blast radius to exactly one new file.

Numbering matches ``/decision-record``: the next id is ``max(existing) + 1`` per
type, gap-safe — a missing number in the middle is never reused.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DIR = REPO_ROOT / "docs" / "product"
TEMPLATES_DIR = PRODUCT_DIR / "templates"


@dataclass(frozen=True)
class TypeSpec:
    """Per-artifact-type layout: where files live, their id prefix, the
    template to copy, and the frontmatter key/placeholder for the parent link
    (``None`` for top-level epics)."""

    directory: str
    prefix: str
    template: str
    parent_field: tuple[str, str] | None


TYPE_SPEC: dict[str, TypeSpec] = {
    "epic": TypeSpec("epics", "EPIC", "epic-template.md", None),
    "story": TypeSpec("stories", "STORY", "user-story-template.md", ("epic", "EPIC-NNN")),
    "task": TypeSpec("tasks", "TASK", "task-template.md", ("story", "STORY-NNN")),
    "plan": TypeSpec(
        "implementation-plans",
        "PLAN",
        "implementation-plan-template.md",
        ("covers", "<EPIC-NNN | STORY-NNN | TASK-NNN>"),
    ),
}

# The status lifecycle the ``--status`` flag accepts. Kept identical to
# ``scripts/validate_product_items.py`` VALID_STATUSES (and the template comment)
# by a drift-guard test, so a ``--status`` scaffold can never write a value the
# gate would then reject.
VALID_STATUSES = {"Proposed", "Ready", "In Progress", "In Review", "Done", "Archived"}

# Characters that force YAML double-quoting when they appear in a frontmatter
# title. A leading indicator (or a leading/trailing space) is unsafe anywhere;
# a ``#`` (comment) or ``:`` (mapping) anywhere in the value would otherwise
# truncate or mis-parse it. Everything else (parens, commas, an em-dash, a
# trailing ``!``) is safe as a plain block scalar and left unquoted.
_YAML_INDICATOR_START = set("-?:,[]{}#&*!|>'\"%@` ")


def slugify(title: str) -> str:
    """Kebab-case a title: lowercase, non-alphanumeric runs → single hyphen."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _needs_quoting(value: str) -> bool:
    """True if ``value`` can't be a plain YAML scalar in ``key: value`` form."""
    if value == "" or value != value.strip():
        return True
    if value[0] in _YAML_INDICATOR_START:
        return True
    return "#" in value or ":" in value


def yaml_title(value: str) -> str:
    """Render a title as a YAML-safe frontmatter scalar.

    Plain-safe titles pass through unquoted (keeping the common case clean);
    anything with a YAML indicator (a ``#`` PR reference, a ``:``) is emitted
    double-quoted with escaping so it round-trips instead of being truncated as
    a comment (TASK-011).
    """
    if not _needs_quoting(value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def next_id(product_dir: Path, item_type: str) -> str:
    """Return the next zero-padded id for ``item_type`` as ``max + 1``.

    Gap-safe: with ``001`` and ``003`` present, returns ``004`` — never ``002``.
    An empty (or missing) directory yields ``001``. **Archive-aware**: the scan
    recurses, so an id under ``<type>/archive/`` still counts and is never reused
    (archiving a shipped ``EPIC-006`` must not let the next epic become ``006``).
    """
    spec = _spec(item_type)
    directory = product_dir / spec.directory
    pattern = re.compile(rf"^{spec.prefix}-(\d+)")
    highest = 0
    if directory.is_dir():
        for entry in directory.rglob(f"{spec.prefix}-*"):
            match = pattern.match(entry.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return f"{highest + 1:03d}"


def fill_template(
    text: str,
    *,
    spec: TypeSpec,
    item_id: str,
    title: str,
    today: str,
    parent_value: str | None = None,
    roadmap_ref: str | None = None,
    owner: str | None = None,
    status: str | None = None,
) -> str:
    """Substitute the template's placeholder tokens with concrete values.

    Unset optional fields keep their template placeholder so they stay
    obviously-fillable by hand. The frontmatter title is emitted YAML-safe
    (``<short title>``); the human ``<Title>`` heading stays plain text.
    """
    out = text.replace(f"{spec.prefix}-NNN", item_id)
    out = out.replace("<short title>", yaml_title(title)).replace("<Title>", title)
    out = out.replace("YYYY-MM-DD", today)
    if owner:
        out = out.replace("<name>", owner)
    if status:
        out = out.replace("status: Proposed", f"status: {status}", 1)
    if spec.parent_field and parent_value:
        key, placeholder = spec.parent_field
        out = out.replace(f"{key}: {placeholder}", f"{key}: {parent_value}")
    if roadmap_ref:
        out = out.replace(
            "roadmap_ref: <roadmap.md item id, e.g. X4>",
            f"roadmap_ref: {roadmap_ref}",
        )
    return out


def create(
    item_type: str,
    title: str,
    *,
    product_dir: Path = PRODUCT_DIR,
    templates_dir: Path = TEMPLATES_DIR,
    today: str,
    parent: str | None = None,
    covers: str | None = None,
    roadmap_ref: str | None = None,
    owner: str | None = None,
    standalone: bool = False,
    status: str | None = None,
) -> Path:
    """Create one new artifact file and return its path.

    ``parent`` links a story→epic or task→story; ``covers`` links a plan→item.
    ``standalone`` nulls that parent link (``story: none`` / ``epic: none``).
    ``status`` stamps the initial lifecycle state (default keeps ``Proposed``).
    Refuses to overwrite an existing file (defensive — ``next_id`` is gap-safe).
    """
    spec = _spec(item_type)
    item_id = f"{spec.prefix}-{next_id(product_dir, item_type)}"
    dest = product_dir / spec.directory / f"{item_id}-{slugify(title)}.md"
    if dest.exists():
        raise FileExistsError(f"refusing to overwrite existing artifact: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)  # backlog dirs are created on first artifact

    template_text = (templates_dir / spec.template).read_text(encoding="utf-8")
    parent_value = covers if spec.prefix == "PLAN" else parent
    if standalone:
        parent_value = "none"
    content = fill_template(
        template_text,
        spec=spec,
        item_id=item_id,
        title=title,
        today=today,
        parent_value=parent_value,
        roadmap_ref=roadmap_ref,
        owner=owner,
        status=status,
    )
    dest.write_text(content, encoding="utf-8")
    return dest


def _id_from_path(path: Path) -> str:
    """Extract the artifact id (e.g. ``TASK-006``) from its filename."""
    match = re.match(r"^([A-Z]+-\d{3})-", path.name)
    if match is None:
        raise ValueError(f"cannot derive an artifact id from {path.name!r}")
    return match.group(1)


def create_with_plan(
    item_type: str,
    title: str,
    *,
    product_dir: Path = PRODUCT_DIR,
    templates_dir: Path = TEMPLATES_DIR,
    today: str,
    parent: str | None = None,
    roadmap_ref: str | None = None,
    owner: str | None = None,
    standalone: bool = False,
    status: str | None = None,
) -> tuple[Path, Path]:
    """Create ``item_type`` **and** its paired Implementation Plan, cross-linking
    ``plan:`` ↔ ``covers:`` between the two.

    Stays within the script's "new files only" blast radius: it creates two new
    files and edits **only** those two — it never touches a pre-existing parent
    document or the roadmap (those remain the skill's with-confirm job).
    """
    if item_type == "plan":
        raise ValueError("--with-plan cannot be used when creating a plan")

    item_path = create(
        item_type,
        title,
        product_dir=product_dir,
        templates_dir=templates_dir,
        today=today,
        parent=parent,
        roadmap_ref=roadmap_ref,
        owner=owner,
        standalone=standalone,
        status=status,
    )
    item_id = _id_from_path(item_path)

    plan_path = create(
        "plan",
        title,
        product_dir=product_dir,
        templates_dir=templates_dir,
        today=today,
        covers=item_id,
        owner=owner,
        status=status,
    )
    plan_id = _id_from_path(plan_path)

    # Wire the item's `plan:` field back to the new plan (edits the new item
    # file only — the plan's `covers:` was set at creation via `covers=`).
    item_text = item_path.read_text(encoding="utf-8")
    item_text = item_text.replace("plan: <PLAN-NNN or none>", f"plan: {plan_id}", 1)
    item_path.write_text(item_text, encoding="utf-8")

    return item_path, plan_path


def _spec(item_type: str) -> TypeSpec:
    try:
        return TYPE_SPEC[item_type]
    except KeyError:
        raise ValueError(
            f"unknown type {item_type!r}; expected one of {sorted(TYPE_SPEC)}"
        ) from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a product-management artifact from its template."
    )
    parser.add_argument("type", choices=sorted(TYPE_SPEC), help="artifact type")
    parser.add_argument("--title", required=True, help="artifact title")
    parent_group = parser.add_mutually_exclusive_group()
    parent_group.add_argument("--parent", help="parent id (epic for a story, story for a task)")
    parent_group.add_argument(
        "--standalone",
        action="store_true",
        help="no parent — sets story:/epic: none (story or task only)",
    )
    parser.add_argument("--covers", help="covered id for a plan (EPIC-/STORY-/TASK-)")
    parser.add_argument(
        "--status",
        choices=sorted(VALID_STATUSES),
        help="initial status (default: Proposed)",
    )
    parser.add_argument(
        "--with-plan",
        dest="with_plan",
        action="store_true",
        help="also create the paired Implementation Plan and wire plan: <-> covers:",
    )
    parser.add_argument("--roadmap-ref", dest="roadmap_ref", help="roadmap.md item id, e.g. X4")
    parser.add_argument("--owner", help="owner name")
    parser.add_argument("--today", help="ISO date override (defaults to today)")
    args = parser.parse_args(argv)

    if args.standalone and args.type in ("epic", "plan"):
        parser.error(
            "--standalone applies to a story or task (epics have no parent; plans --covers)"
        )
    if args.with_plan and args.type == "plan":
        parser.error("--with-plan cannot be used when creating a plan")

    today = args.today or _dt.date.today().isoformat()

    if args.with_plan:
        item_path, plan_path = create_with_plan(
            args.type,
            args.title,
            today=today,
            parent=args.parent,
            roadmap_ref=args.roadmap_ref,
            owner=args.owner,
            standalone=args.standalone,
            status=args.status,
        )
        print(item_path)
        print(plan_path)
        return 0

    path = create(
        args.type,
        args.title,
        today=today,
        parent=args.parent,
        covers=args.covers,
        roadmap_ref=args.roadmap_ref,
        owner=args.owner,
        standalone=args.standalone,
        status=args.status,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
