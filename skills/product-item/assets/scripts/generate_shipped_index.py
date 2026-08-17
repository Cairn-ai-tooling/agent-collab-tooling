"""Generate ``docs/product/shipped.md`` — the completed-epics index.

Why this script exists
======================

When an Epic ships, its whole subtree is archived under ``docs/product/<type>/archive/`` (see the
``close-out-sweep`` skill and ``docs/product/README.md``). The roadmap then tracks *outstanding*
work only and the CHANGELOG holds the feature-level narrative — so nothing lists the shipped
Epics in one place. This script derives that list mechanically from the source of truth (the
``Done`` Epics themselves) instead of asking anyone to hand-maintain it.

It scans every Epic — active dir **and** ``epics/archive/`` (recursively) — keeps the ones whose
``status`` is ``Done``, sorts them by id, and writes a Markdown table to ``shipped.md``. The file
is generated: never hand-edit it, just re-run this. Self-contained (stdlib + ``pyyaml``).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DIR = REPO_ROOT / "docs" / "product"


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


def collect_shipped(product_dir: Path) -> list[dict[str, str]]:
    """Every ``Done`` epic (active dir or ``archive/``) as index rows, sorted by id."""
    epics_dir = product_dir / "epics"
    rows: list[dict[str, str]] = []
    if not epics_dir.is_dir():
        return rows
    for path in sorted(epics_dir.rglob("*.md")):
        meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        if meta.get("status") != "Done":
            continue
        rows.append(
            {
                "roadmap_ref": str(meta.get("roadmap_ref", "—")),
                "id": str(meta.get("id", "")),
                "title": str(meta.get("title", "")),
                "relpath": path.relative_to(product_dir).as_posix(),
            }
        )
    rows.sort(key=lambda r: r["id"])
    return rows


def render(rows: list[dict[str, str]]) -> str:
    """Render the shipped-index Markdown from the collected rows."""
    lines = [
        "# Shipped",
        "",
        "Completed epics, **generated** from `Done` epics under `docs/product/epics/`",
        "(including `epics/archive/`). Do not edit by hand — run",
        "`uv run python scripts/generate_shipped_index.py`. The",
        "[CHANGELOG](../../CHANGELOG.md) holds the feature-level narrative; the",
        "[roadmap](../roadmap.md) holds outstanding work only.",
        "",
        "| Roadmap | Epic | Title |",
        "| ------- | ---- | ----- |",
    ]
    for row in rows:
        epic_cell = f"[{row['id']}]({row['relpath']})" if row["relpath"] else row["id"]
        lines.append(f"| {row['roadmap_ref']} | {epic_cell} | {row['title']} |")
    if not rows:
        lines.append("| — | — | _(none yet)_ |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    product_dir = Path(args[0]) if args else PRODUCT_DIR
    rows = collect_shipped(product_dir)
    (product_dir / "shipped.md").write_text(render(rows), encoding="utf-8")
    print(f"wrote {product_dir / 'shipped.md'} ({len(rows)} shipped epic(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
