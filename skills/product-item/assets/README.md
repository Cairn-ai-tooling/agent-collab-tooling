# Product-management workflow

This directory holds the project's **backlog** — the tracked work artifacts that sit between a
one-line roadmap item and shipped code. It is the counterpart to [`docs/decisions/`](../decisions/)
(ADRs, the *why*) and [`CHANGELOG.md`](../../CHANGELOG.md) (what shipped).

Outstanding work lives as one line per item in [`docs/roadmap.md`](../roadmap.md) (Now / Next /
Later). When work on a line starts, it is **graduated** into a tracked artifact here.

## The loop

```text
docs/roadmap.md  (Now / Next / Later)
      │  graduate a row via /product-item
      ▼
EPIC ──► STORY ──► TASK ──► PLAN ──► code + CHANGELOG (+ ADR)
```

- **Epic** — a high-level initiative (maps to one roadmap row via `roadmap_ref`).
- **User Story** — a user-facing increment of an Epic.
- **Task** — an engineering unit of a Story (carries the Definition of Done).
- **Implementation Plan** — the Context → Approach → Files → Verification plan for an Epic/Story/Task
  (carries the Verification/closure check). Mirrors `superpowers:writing-plans`, if that skill is installed.

Not every item needs all four levels — a small change can be a single standalone Task. Use the
smallest structure that keeps the work legible.

## Layout

```text
docs/product/
  README.md                 # this file
  templates/                # the four artifact templates (source of truth)
  epics/                    # EPIC-NNN-<slug>.md          ─┐
  stories/                  # STORY-NNN-<slug>.md          │ created on first
  tasks/                    # TASK-NNN-<slug>.md           │ artifact of each type
  implementation-plans/     # PLAN-NNN-<slug>.md          ─┘
```

## Creating an artifact

Use the **`/product-item`** skill — it handles the judgement (type, title, which parent to wire up)
and calls the deterministic scaffolder:

```bash
uv run python scripts/new_product_item.py <epic|story|task|plan> --title "<title>" \
  [--parent <ID>] [--covers <ID>] [--roadmap-ref <ID>] [--owner "<name>"]
```

The scaffolder computes the next **gap-safe** id (`max + 1` per type — a missing middle number is
never reused), copies the right template, fills `id`/`title`/`created`/`status`/parent, and refuses
to overwrite an existing file. Wiring the child into its parent (`stories:`/`tasks:` lists +
checklists) and adding the `→ <ID>` roadmap pointer are confirm-first edits the skill makes.

## Status lifecycle

`Proposed` → `Ready` → `In Progress` → `In Review` → `Done` → `Archived`

Set in the artifact's `status:` frontmatter. `Proposed` = captured; `Ready` = scoped and agreed;
`Done` = shipped and verified; `Archived` = superseded/abandoned (kept for history).

## Integrity gate

```bash
uv run python scripts/validate_product_items.py
```

A **structural, lenient** check: duplicate ids, dangling/mis-typed `epic:`/`story:`/`covers:` links,
invalid statuses, filename≠id. It deliberately tolerates unfilled placeholders (`EPIC-NNN`, `<...>`,
`none`, `[]`) so a freshly-scaffolded `Proposed` artifact passes. It runs in pre-commit and is
self-contained (only `pyyaml`), so it needs no project code.

## The closure check

Every Task/Plan carries this bar; clear it before calling the work **done** (the same bar we hold
all our work to):

- **Converged** — the end state is more ordered than the start (one source of truth, not two).
- **Legible** — the result maps 1:1 to the stated intent, with no "sort of".
- **Closed** — verified by *running something*, not asserted.
- **Edges surfaced** — remaining rough bits are named, not hidden.

## Related

- `/decision-record` → an ADR in [`docs/decisions/`](../decisions/) for non-obvious architectural
  choices.
- `/changelog` → a `[Unreleased]` entry in [`CHANGELOG.md`](../../CHANGELOG.md) for anything
  user-facing or notable.
