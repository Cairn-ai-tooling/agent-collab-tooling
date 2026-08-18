---
name: close-out-sweep
description: Use when retiring completed work from a docs/product/ backlog in one pass — archiving every shipped (Done) Epic and its whole subtree into per-type archive/ dirs, regenerating the shipped index, and pruning the roadmap. Trigger whenever someone says "close out the backlog", "archive the completed/shipped epics", "sweep the backlog", "retire the done epics", "regenerate the shipped index", or "clean up docs/product now that X shipped". It is the batch counterpart to /product-item (which creates artifacts; this graduates them out once they're Done).
when_to_use: When one or more Epics have shipped and should leave the active backlog — to keep docs/product/ focused on outstanding work while preserving shipped Epics (and gap-safe numbering) under archive/. Pairs with [[product-item]] (creates and archive-aware-numbers the artifacts) and [[changelog]] (the shipped narrative lives there).
---

# Close-out Sweep

Retire completed work from the `docs/product/` backlog in a single pass. For every **active Epic
whose `status` is `Done`**, this moves the Epic *and its whole subtree* (its stories, tasks, and
implementation plan) into per-type `archive/` dirs, regenerates the generated shipped index, and
drops the Epic's roadmap row. It is the batch counterpart to `[[product-item]]`: that skill
*creates* artifacts; this one graduates them *out* once they've shipped.

Archiving is **epic-granular** — a Story and its Tasks always move together with their Epic, so
the move never creates an active→archived dangling link. Numbering stays gap-safe because
`[[product-item]]`'s scanners recurse into `archive/`, so an archived id is still counted and
never reused.

## When to invoke

- One or more Epics have shipped and should leave the active backlog.
- The user asks to archive/retire completed epics, sweep the backlog, or regenerate `shipped.md`.
- Nothing is `Done`? Then there's nothing to sweep — say so (the sweep is a safe no-op).

## Prerequisites

- The backlog must be under **git** (the sweep uses `git mv` to preserve history).
- `[[product-item]]` must be bootstrapped in the repo — this sweep reuses its
  `generate_shipped_index.py` and depends on its archive-aware scanners.

## Procedure

1. **Confirm what's genuinely done.** Only an Epic with `status: Done` (and its whole subtree
   marked `Done`) gets swept. A partially-finished Epic **stays active** — don't archive live
   work. If an Epic looks finished but its subtree isn't all `Done`, help the user flip the
   genuinely-complete ones first (that's `[[product-item]]`'s lifecycle); the dry-run flags any
   subtree member that isn't `Done` yet so you can catch a premature close.
2. **Dry-run — always first.** Run the bundled script in plan-only mode. It ships with this skill;
   run it **in place** from `assets/scripts/close_out_sweep.py` (substitute this skill's real
   install path for `<skill>`), passing the backlog dir:

   ```bash
   uv run --with pyyaml python <skill>/assets/scripts/close_out_sweep.py docs/product
   ```

   It lists each Done Epic and the exact files its subtree would archive, and warns about any
   member that isn't `Done`. It writes **nothing** in this mode.
3. **Review and confirm.** Show the plan. If the dry-run flags not-`Done` members, surface that
   before proceeding — it usually means an Epic was marked `Done` prematurely. Get an explicit
   go-ahead (this moves files and edits the roadmap).
4. **Apply.** On confirmation, re-run with `--apply`:

   ```bash
   uv run --with pyyaml python <skill>/assets/scripts/close_out_sweep.py docs/product --apply
   ```

   For each Done Epic the script: `git mv`s its whole subtree into
   `docs/product/{epics,stories,tasks,implementation-plans}/archive/`; regenerates
   `docs/product/shipped.md` (reusing `[[product-item]]`'s `generate_shipped_index.py`); and
   removes the Epic's `→ EPIC-NNN` row from `docs/roadmap.md` (the roadmap tracks outstanding work
   only; the `[[changelog]]` keeps the feature narrative).
5. **Report and hand off the commit.** Summarize what moved. The sweep **does not commit** — the
   `git mv`s are staged and the regen/roadmap edits are in the working tree; tell the user to
   review with `git status` and commit (e.g. "Archive shipped epics EPIC-004, EPIC-006").

## What it does not touch

- **Active work** — only `Done` Epics and their subtrees move; everything else stays put.
- **`shipped.md` by hand** — it's generated from `Done` epics; never hand-edit it, just re-run.
- **The CHANGELOG** — the shipped narrative lives there and is out of scope for the sweep.
- **Committing** — left to the user, so the move can be reviewed first.

## Acceptance checklist

- A dry-run was shown and confirmed before any `git mv`.
- Only `Done` Epics moved; each moved as a **whole subtree** (no active→archived dangling links).
- Not-`Done` subtree members were surfaced, not silently archived.
- `shipped.md` was regenerated (not hand-edited) and the shipped Epics' roadmap rows were removed.
- A re-run with nothing newly `Done` is a **no-op**.
- Numbering stays gap-safe across active + archived (verify with `[[product-item]]`'s scanners).

Related: batch counterpart to `[[product-item]]`; the shipped narrative belongs in `[[changelog]]`.
