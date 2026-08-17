---
name: product-item
description: Use when creating or scaffolding a backlog artifact — an Epic, User Story, Task, or Implementation Plan — or when graduating a docs/roadmap.md item into a tracked artifact. Scaffolds the next-numbered file from docs/product/templates/, wires parent/child links, and adds a roadmap pointer — the same shape as /decision-record but for backlog artifacts.
when_to_use: When someone says "create an epic/user story/task/implementation plan", "add a product item", "scaffold a backlog item", "turn this roadmap item into an epic/story/task", or "new EPIC/STORY/TASK/PLAN" — and when breaking an Epic into Stories or a Story into Tasks.
---

# Product Item (backlog artifact scaffolder)

Creates one product-management artifact — **Epic**, **User Story**, **Task**, or
**Implementation Plan** — from the templates in `docs/product/templates/`, with correct
numbering and links. It is the backlog counterpart to `[[decision-record]]` (ADRs) and pairs
with `[[changelog]]` when the work ships something user-facing.

The deterministic part (next id, template fill, no-overwrite) is done by
`scripts/new_product_item.py`. This skill handles the judgement: which type, the title, which
parent to wire up, and the roadmap pointer.

## When to invoke

- Graduating a `docs/roadmap.md` item (Now/Next/Later) into a tracked artifact.
- Creating any Epic, User Story, Task, or Implementation Plan.
- Breaking an Epic into Stories, or a Story into Tasks.

See `docs/product/README.md` for the workflow this fits into (Epic → Story → Task → Plan →
code + CHANGELOG (+ ADR)) and the status lifecycle.

## Inputs

Gather from the invocation; **only ask for what's missing**, and ask concisely:

- **type** (required) — `epic` | `story` | `task` | `plan`.
- **title** (required).
- **parent** (optional) — the epic id for a story, the story id for a task.
- **covers** (optional) — for a plan, the `EPIC-`/`STORY-`/`TASK-` id it plans.
- **roadmap-ref** (optional) — the `docs/roadmap.md` row id, e.g. `X4` (fills the Epic's
  `roadmap_ref` frontmatter field).
- **owner** (optional) — defaults to leaving the template placeholder.
- **status** (optional) — initial lifecycle state (`Proposed` | `Ready` | `In Progress` |
  `In Review` | `Done` | `Archived`); defaults to `Proposed`. Use `--status` to skip a manual edit.
- **standalone** (optional, story/task only) — no parent; sets `epic:`/`story:` to `none`. Use
  `--standalone` instead of `--parent` for an orphaned item.
- **with-plan** (optional, not for `plan`) — also create the paired Implementation Plan and
  cross-wire `plan:` ↔ `covers:` in one step. Use `--with-plan`.

Never invent a required field. If it's missing, ask — briefly.

## Procedure

0. **Bootstrap the workflow if missing (idempotent).** This skill is self-contained: it bundles the
   canonical templates, scripts, README, and a roadmap seed under `assets/` (next to this file) so it
   works in *any* repo. If `docs/product/` is absent, seed the repo from the bundle **without
   overwriting anything that already exists** (confirm first):
   - `assets/templates/*` → `docs/product/templates/`
   - `assets/scripts/*` → `scripts/`
   - `assets/README.md` → `docs/product/README.md`
   - `assets/roadmap-template.md` → `docs/roadmap.md` (only if no roadmap exists yet)

   The scripts depend only on `pyyaml` (no application-package import), so they run as-is — this
   includes `scripts/validate_product_items.py`, the self-contained integrity gate (see step 5).
   Then continue. If `docs/product/` already exists, skip bootstrap.
1. **Create the artifact.** Run the scaffolder and capture the printed path:

   ```bash
   uv run python scripts/new_product_item.py <type> --title "<title>" \
     [--parent <ID> | --standalone] [--covers <ID>] [--roadmap-ref <ID>] \
     [--owner "<name>"] [--status "<status>"] [--with-plan]
   ```

   It computes the next gap-safe id, copies the right template, fills
   `id`/`title`/`created`/`status`/parent, and refuses to overwrite an existing file. Titles
   containing YAML-significant characters (a `#` PR reference like "PR #30", or a `:`) are
   emitted quoted so the frontmatter round-trips instead of truncating. `--with-plan` prints two
   paths (the item and its plan).
2. **Wire the parent link — with confirm, and only if the target exists. Never duplicate an
   existing link.** After confirming with the user:
   - **story under an epic:** add the new `STORY-NNN` to the epic's `stories:` frontmatter list
     **and** its `## Child stories` checklist.
   - **task under a story:** add the new `TASK-NNN` to the story's `tasks:` list **and** its
     `## Tasks` checklist.
   - **plan covering an item:** set that item's `plan:` frontmatter field to the new `PLAN-NNN`.
   Check for the link first; if it's already present, skip (idempotent).
3. **Add the roadmap pointer — with confirm.** If `--roadmap-ref` was given and that row exists
   in `docs/roadmap.md`, append a one-line "→ `<ID>`" pointer to that row so the backlog links
   forward to the artifact. Skip if already present.
4. **Report the created path.** Do **not** commit — leave that to the user.
5. **Run the integrity gate.** Validate the backlog is still self-consistent (no duplicate ids,
   dangling links, or invalid statuses):

   ```bash
   uv run python scripts/validate_product_items.py
   ```

   It is structural and lenient — a freshly-scaffolded `Proposed` artifact passes. Report any
   violation it surfaces rather than silently proceeding.

## The closure check

Every artifact this skill creates carries a Definition of Done (Tasks) / Verification (Plans)
that must clear this bar before the work is called *done* — the same bar we hold our own work
to:

- **Converged** — the end state is more ordered than the start (one source of truth, not two).
- **Legible** — the result maps 1:1 to the stated intent, with no "sort of".
- **Closed** — it was verified by *running something*, not asserted.
- **Edges surfaced** — remaining rough bits are named, not hidden.

When helping complete a Task or Plan, hold it to these four before ticking it done.

## Closing out shipped work

When an Epic is genuinely finished it graduates *out* of the active backlog: set `status: Done`
on the epic and its whole subtree, `git mv` that subtree into the per-type `archive/` dirs
(`docs/product/<type>/archive/`), regenerate the shipped index, and drop its `docs/roadmap.md`
row (the roadmap tracks outstanding work only; the CHANGELOG keeps the narrative). The bundled
`scripts/generate_shipped_index.py` derives `docs/product/shipped.md` from every `Done` epic —
it recurses `epics/archive/`, so **never hand-edit** that file, just re-run it. Archive one epic
by hand; to sweep **all** completed epics in one pass, use `[[close-out-sweep]]`.

Archiving is safe for numbering and links: both `scripts/new_product_item.py` and
`scripts/validate_product_items.py` recurse into `archive/`, so archived ids still count (never
reused) and cross-links resolve across the active/archive boundary.

## Acceptance checklist

- Numbering is **max + 1** per type and **gap-safe** — a missing middle number is never reused;
  an empty type-dir starts at `001`. The scan is **archive-aware** (recurses `<type>/archive/`),
  so an archived id is still counted and never reused.
- Re-running never overwrites an existing artifact (the scaffolder refuses).
- Parent/roadmap links are added **only to pre-existing files** and are **never duplicated**.
- The created artifact's frontmatter is accurate (id, title, created, status, parent) — a title
  with a `#` or `:` is quoted, not truncated.
- The created Task/Plan carries the closure check.
- `scripts/validate_product_items.py` reports no violations after the artifact is created.

Related: pairs with `[[decision-record]]` (ADRs) and `[[changelog]]` (release notes);
`[[close-out-sweep]]` retires the Epics this skill creates once they ship.
