---
name: github-backlog-sync
description: Use when mirroring a local product backlog (docs/product/ Epics, User Stories, Tasks, Plans created by /product-item) out to GitHub Issues, or onto a GitHub Project board — creating or updating issues, keeping status in sync, and recording the issue number back on each artifact. Trigger whenever someone says "push these to GitHub Issues", "sync the backlog to GitHub", "create issues for these tasks/epics", "put this on the GitHub Project board", "mirror docs/product to GitHub", or asks whether the backlog is big enough to move onto GitHub. The local Markdown stays the source of truth; GitHub is the mirror.
when_to_use: When a docs/product/ backlog should be visible on GitHub — issues for assignment/comments/PR cross-references, or a Project board for a cross-cutting view — and when deciding whether a project is large enough to warrant that. Pairs with [[product-item]] (which creates the artifacts) and complements [[shared-task-tracking]] (session-local coordination vs. this persistent, external mirror).
---

# GitHub Backlog Sync

Mirror the local `docs/product/` backlog — the Epics, User Stories, Tasks, and Implementation
Plans that `[[product-item]]` scaffolds — out to **GitHub Issues**, and optionally onto a
**GitHub Project** board. The local Markdown files stay the **source of truth**; each GitHub
Issue is a mirror that links back to its artifact. This is the persistent, external-visibility
counterpart to `[[shared-task-tracking]]` (which is session-local coordination).

Sync is **idempotent**: the Issue number is recorded back into the artifact's frontmatter
(`github_issue:`), so re-running updates the existing Issue instead of creating a duplicate. This
mirrors the "record the id, never duplicate" discipline `[[product-item]]` already uses for
parent/roadmap links.

## When to invoke

- The user asks to push/mirror/sync `docs/product/` artifacts to GitHub Issues or a Project.
- New or changed artifacts need their Issues created or brought up to date.
- The user asks whether the backlog is big enough to move onto GitHub (see **The size metric**).

If there is no `docs/product/` backlog yet, this skill has nothing to sync — point the user at
`[[product-item]]` to create artifacts first.

## The size metric — should this project use GitHub at all?

A local Markdown backlog is enough for small efforts, and pushing everything to GitHub adds
overhead (noise, two places to look). **Recommend** graduating to GitHub Issues when **any** of
these hold — otherwise say so and suggest staying local:

- more than ~**15–20 open** tracked artifacts, or
- more than **1 active Epic**, or
- more than **1 person/agent** working the backlog (needs shared, external visibility), or
- the work **spans multiple sprints** / more than ~2 weeks, or
- **external stakeholders** need read access.

Use a **GitHub Project board** specifically once there is **more than 1 Epic** and a
cross-cutting status/roadmap view is wanted; below that, plain Issues (or staying local) suffice.
The sync script prints these counts, so lead with the numbers, then the recommendation — don't
push GitHub onto a five-task backlog.

## Prerequisites

Pick the backend that's available (the script does this for you):

- **`gh` CLI** (preferred) — installed and authenticated (`gh auth status`). Zero-config; the
  bundled script drives it. Confirm the target repo (`gh repo view` or an explicit `--repo`).
- **GitHub MCP server** — if `gh` is absent but the GitHub MCP tools are connected, follow the
  **MCP fallback** section: you perform the same steps the script would, using the MCP tools and
  the mapping rules below.

If neither is available, stop and tell the user what to set up — do not guess.

## Inputs

Gather from the invocation; ask only for what's missing:

- **repo** (required) — `owner/name`. Default to the current repo's origin if unambiguous.
- **product dir** (optional) — defaults to `docs/product`.
- **project** (optional) — a GitHub Project number to add issues to and drive its status field.
- **scope** (optional) — all artifacts, or a subset (a type, an Epic and its children, a single id).

## Procedure

1. **Resolve the backend and repo.** Prefer `gh`; confirm auth and the target `owner/name`.
2. **Dry-run first — always.** Run the script in its default (plan-only) mode to produce the
   sync plan and the backlog counts:

   ```bash
   uv run python scripts/sync_github_items.py --repo <owner/name> [--project <N>]
   ```

   It prints, per artifact: `create` (no `github_issue:` yet) or `update` (has one), the target
   title/labels/state, and — if `--project` was given — the Project status. It writes **nothing**
   in this mode.
3. **Surface the metric + plan, and confirm.** Show the counts and the plan. If the backlog is
   below the size metric, say so and recommend staying local before doing anything. Get explicit
   confirmation before writing to GitHub — this reaches an external, shared system.
4. **Apply.** On confirmation, re-run with `--apply`:

   ```bash
   uv run python scripts/sync_github_items.py --repo <owner/name> [--project <N>] --apply
   ```

   For each artifact the script: creates or updates the Issue; sets its open/closed state from
   the artifact status; (with `--project`) adds it to the board and sets the status field; and
   **writes the `github_issue:` / `github_project_item:` values back** into the artifact
   frontmatter so the next run is idempotent.
5. **Report.** List what was created vs. updated and the Issue URLs. The frontmatter writeback is
   a local edit — leave committing to the user.

## Mapping rules

These define how an artifact becomes an Issue; the script and the MCP fallback both follow them.

- **Title** — `` `<ID>` <title> `` (e.g. `EPIC-004 Payments platform`) so the Issue is greppable
  by artifact id.
- **Body** — rendered from `assets/templates/issue-body-template.md`: a backlink to the artifact
  path, the type/status/parent, and the artifact's own content. The whole body is **regenerated**
  on each update; human discussion belongs in Issue **comments**, which the sync never touches.
- **Label** — the artifact type: `epic` / `story` / `task` / `plan`.
- **State** — `Done` and `Archived` close the Issue; every other status leaves it open.
- **Project status** (only with `--project`) — the artifact `status:` maps 1:1 to a Project
  single-select field of the same name (`Proposed`, `Ready`, `In Progress`, `In Review`, `Done`,
  `Archived`). Create those options on the board once if they don't exist.

## Idempotency & safety

- The **only** local write is recording `github_issue:` / `github_project_item:` into frontmatter.
  The script never edits an artifact's other fields, its parent, or the roadmap.
- Re-running with no local changes is a **no-op** (everything already has its issue number).
- Default is plan-only; mutations require `--apply`. Never `--apply` without the user's OK.
- One-way sync (local → GitHub) only. Changes made **on** GitHub are not pulled back; if a status
  differs, the local artifact wins on the next sync.

## MCP fallback (no `gh`)

When only the GitHub MCP server is available, do what the script would, in the same order, using
the MCP Issue/Project tools: read the artifacts, compute create-vs-update from `github_issue:`,
apply the **Mapping rules** above, then edit each artifact's frontmatter to record the returned
issue number (and project item id). Keep the same confirm-first, plan-then-apply discipline.

## Acceptance checklist

- A dry-run was shown and confirmed **before** any GitHub write.
- The size metric was reported; GitHub was recommended only when the thresholds were met.
- No duplicate issues: artifacts with a `github_issue:` were updated, not recreated.
- Every synced artifact carries its `github_issue:` (and `github_project_item:` when a Project
  was used) in frontmatter afterward.
- Issue state matches artifact status (`Done`/`Archived` → closed).
- Only frontmatter was written locally; nothing was committed by the skill.

Related: consumes artifacts from `[[product-item]]`; complements `[[shared-task-tracking]]`.
