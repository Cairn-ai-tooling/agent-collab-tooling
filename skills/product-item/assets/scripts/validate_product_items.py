"""Integrity gate for the `docs/product/` backlog artifacts.

Why this script exists
======================

The product-management workflow (``docs/product/README.md``) tracks work as
numbered Markdown artifacts — Epics, User Stories, Tasks, Implementation Plans —
whose YAML frontmatter carries the id, status, and the cross-links that make the
set navigable. The ``/product-item`` skill scaffolds them correctly, but nothing
stops a later hand-edit from introducing a duplicate id, a dangling
``epic:`` / ``covers:`` link, a typo'd status, or a filename that no longer
matches its id. This gate catches that drift at commit time and in CI.

Design: **structural / lenient.** It checks the integrity of *filled* data and
deliberately ignores unfilled scaffold placeholders (``EPIC-NNN``, ``<...>``),
``none``, and empty link lists — those are legitimate work-in-progress, not
errors. So a freshly-scaffolded ``Proposed`` artifact never trips the gate.

The type map (dirs/prefixes), ``slugify``, and the status set are meant to stay
in lock-step with ``scripts/new_product_item.py`` + the templates; a consuming
repo can pin that parity with a small drift-guard test if it wants CI to catch
divergence.

Frontmatter parsing is self-contained (stdlib + ``pyyaml``) so this gate — and
the ``/product-item`` skill that bundles it — runs in any repo with no
dependency on this project's application package.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a Markdown document into its YAML frontmatter and body.

    Returns ``({}, text)`` when the text does not open with a ``---`` fence or the
    fenced block is not a YAML mapping, so a file with no/malformed frontmatter is
    reported rather than crashing.
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n---", 1)
    if len(parts) != 2:
        return {}, text
    front = parts[0][len("---") :]
    body = parts[1].lstrip("\n")
    try:
        meta = yaml.safe_load(front)
    except yaml.YAMLError:
        return {}, text
    if not isinstance(meta, dict):
        return {}, text
    return meta, body


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DIR = REPO_ROOT / "docs" / "product"

VALID_STATUSES = {"Proposed", "Ready", "In Progress", "In Review", "Done", "Archived"}
REQUIRED_KEYS = ("id", "title", "type", "status", "owner", "created")

REAL_ID_RE = re.compile(r"^(EPIC|STORY|TASK|PLAN)-\d{3}$")


@dataclass(frozen=True)
class _Type:
    directory: str
    prefix: str
    fm_type: str  # the value of the `type:` frontmatter field


# Kept in sync with scripts/new_product_item.py TYPE_SPEC via a drift-guard test.
_TYPES: dict[str, _Type] = {
    "epic": _Type("epics", "EPIC", "epic"),
    "story": _Type("stories", "STORY", "story"),
    "task": _Type("tasks", "TASK", "task"),
    "plan": _Type("implementation-plans", "PLAN", "implementation-plan"),
}

# type key -> list of (frontmatter field, allowed target type keys, is_list)
_LINK_FIELDS: dict[str, list[tuple[str, set[str], bool]]] = {
    "epic": [("stories", {"story"}, True)],
    "story": [("epic", {"epic"}, False), ("tasks", {"task"}, True)],
    "task": [("story", {"story"}, False), ("plan", {"plan"}, False)],
    "plan": [("covers", {"epic", "story", "task"}, False)],
}


@dataclass(frozen=True)
class Violation:
    path: Path
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def slugify(title: str) -> str:
    """Kebab-case a title: lowercase, non-alphanumeric runs → single hyphen.

    Mirrors ``scripts/new_product_item.py``; a drift-guard test pins parity.
    """
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _is_real_id(value: object) -> bool:
    """True for a concrete id like ``EPIC-001`` — not a placeholder / none."""
    return isinstance(value, str) and REAL_ID_RE.match(value) is not None


def _is_placeholder_title(title: object) -> bool:
    return isinstance(title, str) and title.strip().startswith("<")


def validate_tree(product_dir: Path) -> list[Violation]:
    """Return all integrity violations across the product artifact tree."""
    violations: list[Violation] = []
    index: dict[str, str] = {}  # id -> type key
    records: list[tuple[str, Path, dict[str, Any]]] = []

    # Pass 1 — parse + per-file structural checks + build the id index.
    # Discovery recurses (rglob) so archived artifacts under ``<type>/archive/`` are validated
    # too, and the single id index lets links resolve across the active/archive boundary.
    for type_key, spec in _TYPES.items():
        directory = product_dir / spec.directory
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.md")):
            meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            if not meta:
                violations.append(Violation(path, "missing or malformed YAML frontmatter"))
                continue
            records.append((type_key, path, meta))

            for key in REQUIRED_KEYS:
                if key not in meta:
                    violations.append(Violation(path, f"missing required frontmatter key: {key}"))

            if "type" in meta and meta["type"] != spec.fm_type:
                actual = meta["type"]
                violations.append(
                    Violation(
                        path,
                        f"type '{actual}' does not match directory (expected '{spec.fm_type}')",
                    )
                )

            if "status" in meta and meta["status"] not in VALID_STATUSES:
                violations.append(Violation(path, f"invalid status: {meta['status']!r}"))

            item_id = meta.get("id")
            if "id" not in meta:
                continue
            if not isinstance(item_id, str) or not re.match(rf"^{spec.prefix}-\d{{3}}$", item_id):
                violations.append(
                    Violation(path, f"invalid id {item_id!r} (expected {spec.prefix}-NNN)")
                )
                continue
            if item_id in index:
                violations.append(Violation(path, f"duplicate id {item_id}"))
            else:
                index[item_id] = type_key

            # Filename must be <id>-<slug>.md; slug checked only when title is filled.
            if not path.name.startswith(f"{item_id}-"):
                violations.append(Violation(path, f"filename does not start with id {item_id}"))
            else:
                title = meta.get("title")
                if isinstance(title, str) and not _is_placeholder_title(title):
                    expected = f"{item_id}-{slugify(title)}.md"
                    if path.name != expected:
                        violations.append(Violation(path, f"filename should be {expected}"))

    # Pass 2 — resolve cross-artifact links (skip placeholders / none / empty).
    for type_key, path, meta in records:
        for field, allowed, is_list in _LINK_FIELDS[type_key]:
            raw = meta.get(field)
            values = (
                raw if (is_list and isinstance(raw, list)) else ([raw] if raw is not None else [])
            )
            for value in values:
                if not _is_real_id(value):
                    continue
                if value not in index:
                    violations.append(
                        Violation(
                            path, f"{field}: '{value}' does not resolve to an existing artifact"
                        )
                    )
                elif index[value] not in allowed:
                    violations.append(
                        Violation(
                            path,
                            f"{field}: '{value}' is a {index[value]}, expected {sorted(allowed)}",
                        )
                    )

    return violations


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    product_dir = Path(args[0]) if args else PRODUCT_DIR
    if not product_dir.is_dir():
        print(f"error: not a directory: {product_dir}", file=sys.stderr)
        return 2

    violations = validate_tree(product_dir)
    if violations:
        print(f"Found {len(violations)} product-item violation(s):", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        return 1

    print("OK: product artifacts validated with no violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
