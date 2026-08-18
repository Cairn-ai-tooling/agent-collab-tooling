---
name: github-backlog-sync
description: Use when mirroring a local product backlog (docs/product/ Epics, User Stories, Tasks, Plans created by /product-item) out to GitHub Issues, or onto a GitHub Project board — creating or updating issues, keeping status in sync, and recording the issue number back on each artifact. Trigger whenever someone says "push these to GitHub Issues", "sync the backlog to GitHub", "create issues for these tasks/epics", "put this on the GitHub Project board", "mirror docs/product to GitHub", or asks whether the backlog is big enough to move onto GitHub. The local Markdown stays the source of truth; GitHub is the mirror.
when_to_use: When a docs/product/ backlog should be visible on GitHub — issues for assignment/comments/PR cross-references, or a Project board for a cross-cutting view — and when deciding whether a project is large enough to warrant that. Pairs with [[product-item]] (which creates the artifacts) and complements [[shared-task-tracking]] (session-local coordination vs. this persistent, external mirror).
---

# GitHub Backlog Sync

Mirror the local `docs/product/` backlog — the Epics, User Stories, Tasks, and Implementation
Plans that `[[product-item]]` scaffolds — out to **GitHub Issues**, and optionally onto a
**GitHub Project** board. The local Markdown files stay the **source of truth**; each Issue is a
mirror that links back. Sync is **idempotent**: the issue number is recorded into the artifact's
frontmatter (`github_issue:`), so re-running updates the existing Issue instead of duplicating it.

## Voice — read this first

You are a capable agent, not a script-runner. Everything below is guidance to apply with
judgment, not a checklist to recite. In practice that means:

- **Be concise and human.** Scale the response to the ask — a one-line "is this worth it?" gets a
  short, warm answer, not a wall of headings. Lead with the answer.
- **Use initiative.** Do the cheap, smart things a thoughtful colleague would: sanity-check the
  repo exists before planning, notice when artifacts are empty stubs, ask what's really behind the
  request. The bundled script handles the mechanics so you can spend attention here.
- **Recommend, don't gatekeep.** Give your honest read (including "I'd stay local"), then let the
  user decide — and offer to do it their way if they disagree.

## When to invoke

- The user asks to push/mirror/sync `docs/product/` artifacts to GitHub Issues or a Project.
- New or changed artifacts need their Issues created or brought up to date.
- The user asks whether the backlog is big enough to move onto GitHub (see the metric below).

If there's no `docs/product/` backlog yet, there's nothing to sync — point them at
`[[product-item]]` to create artifacts first.

## Is GitHub even worth it? (the size metric)

A local Markdown backlog is plenty for small efforts; pushing everything to GitHub adds noise and
a second place to look. So when the backlog is small, **say so and recommend staying local** —
but always **offer to do it anyway** if they want, and if they're just *asking* (not instructing),
ask what's prompting it, in case there's an unspoken need a board wouldn't solve.

Lead with the numbers (the script prints them), then recommend GitHub when **any** hold:

- more than ~**15–20 open** tracked artifacts, or
- more than **1 active Epic**, or
- more than **1 person/agent** on the backlog (shared, external visibility), or
- work **spanning multiple sprints** / more than ~2 weeks, or
- **external stakeholders** need read access.

A **Project board** specifically earns its keep once there's **more than 1 Epic** and you want a
cross-cutting status view.

## Backend & pre-flight

- Prefer the **`gh` CLI** (installed + authenticated). The bundled script drives it.
- **Confirm the repo resolves before planning** — a quick `gh repo view <owner/name>` catches a
  typo or an access problem cheaply, before you've promised anything. Default the repo to the
  current git remote's `origin` when it's unambiguous (that's usually the one they mean). If the
  check fails, surface it **prominently** — a clear heading, the command you ran, and its output —
  so it's obvious and actionable, and stop until it's resolved.
- If `gh` is absent but the **GitHub MCP** tools are connected, follow **MCP fallback** below.
- If neither is available, say what to set up. Don't guess.

## Inputs

Ask only for what's missing: **repo** (`owner/name`, default the origin remote), **product dir**
(default `docs/product`), an optional **project** number, and any **scope** limit (a type, an Epic
and its children, a single id).

## Procedure

1. **Pre-flight** the backend and repo (above).
2. **Dry-run — always first.** Run the bundled script in plan-only mode. It ships with this skill;
   run it **in place** from `assets/scripts/sync_github_items.py` (substitute this skill's real
   install path for `<skill>`). It takes the backlog dir as an argument and finds its template
   relative to itself, so it needs no bootstrap:

   ```bash
   uv run --with pyyaml python <skill>/assets/scripts/sync_github_items.py docs/product --repo <owner/name> [--project <N>]
   ```

   It writes nothing and prints: the backlog counts; per artifact whether it's a **create** (no
   `github_issue:` yet) or **update**; on a re-sync, whether each already-synced artifact has
   **changed** since last sync (unchanged ones are skipped); and advisory flags for **stubs** and
   **status drift** (see below).
3. **Report and confirm — as "what I need before I sync".** Give a tight summary: the size read
   (recommend, don't gatekeep), what will be created vs. updated, and — because this reaches a
   shared, external system — an explicit note that already-synced artifacts are **updated, not
   duplicated**. Then list, as clear actions, anything you need from the user (repo confirmation,
   project details, how to handle stubs/drift). Offer to walk through them interactively. Get an
   explicit go-ahead before writing.
4. **Apply** on confirmation by re-running with `--apply`. The script creates/updates issues, sets
   open/closed state from status, (with `--project`) puts them on the board with the right status,
   and records `github_issue:` / `github_project_item:` / `github_synced_digest:` back into
   frontmatter. Those frontmatter writes are the only local changes — leave committing to the user.
5. **Report** what was created, updated, and skipped, with issue URLs.

## Before you push — three things to catch

The dry-run flags these; handle them with judgment rather than plowing ahead:

- **Stubs.** An artifact still full of `<...>` template placeholders becomes a low-signal Issue.
  When you see stubs, say so, and rather than pushing noise, **offer to fill them out first** —
  hand that to `[[product-item]]`, which owns artifact content (a short question-and-answer pass
  per artifact). Also worth asking: does the real content live somewhere else (a doc, a
  spreadsheet, someone's notes) that should be brought in first?
- **Status drift.** The local `status:` is free text and can drift off the canonical set
  (`Proposed`, `Ready`, `In Progress`, `In Review`, `Done`, `Archived`). The script flags any that
  don't match; surface near-duplicates and reconcile them **before** mapping onto a Project field,
  rather than silently creating odd columns.
- **What changed since last sync.** On a re-sync the script marks each synced artifact
  changed/unchanged (by digesting its title + status + body) and skips the unchanged ones. Use
  that to tell the user what actually moved, not just "re-synced everything".

## Mapping rules

- **Title** — `` `<ID>` <title> `` (e.g. `EPIC-004 Payments platform`), greppable by id.
- **Body** — rendered from `assets/templates/issue-body-template.md`: a backlink, type/status/
  parent, and the artifact's content. Regenerated on each update; discussion lives in Issue
  **comments**, which the sync never touches.
- **Label** — the artifact type (`epic` / `story` / `task` / `plan`).
- **State** — `Done` / `Archived` close the Issue; every other status leaves it open.
- **Project status** (with `--project`) — the artifact `status:` maps 1:1 to a Project
  single-select field of the same name; create missing options once.

## Safety

- The only local writes are the bookkeeping frontmatter fields above — never an artifact's other
  content, its parent, or the roadmap.
- Plan-only by default; mutations need `--apply` and the user's OK.
- One-way sync (local → GitHub). Changes made **on** GitHub aren't pulled back; the local artifact
  wins on the next sync.

## MCP fallback (no `gh`)

When only the GitHub MCP server is available, do what the script would, in the same order, using
the MCP Issue/Project tools: read the artifacts, compute create-vs-update from `github_issue:`,
apply the mapping rules, then record the returned issue number (and project item id) back into
frontmatter. Keep the same pre-flight, plan-then-confirm, stub/drift awareness.

## Acceptance checklist

- The repo was confirmed to resolve before any plan was promised.
- A dry-run was shown and confirmed **before** any GitHub write.
- The size read was given as a recommendation (with an offer to proceed anyway), not a gate.
- Stubs and status drift were surfaced, not silently pushed.
- No duplicate issues: artifacts with a `github_issue:` were updated (or skipped if unchanged).
- Every synced artifact carries its `github_issue:` (and `github_project_item:` with a Project)
  afterward; issue state matches status; only frontmatter was written locally.

Related: consumes artifacts from `[[product-item]]`; complements `[[shared-task-tracking]]`.
