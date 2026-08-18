# 0003 — GitHub sync as a separate sibling skill with a backend-agnostic adapter

**Status:** Accepted (implemented as the `github-backlog-sync` skill)

## Context

`product-item` maintains a local, file-based backlog under `docs/product/`. As a project grows,
teams want that work mirrored to **GitHub Issues** (assignment, comments, commit/PR
cross-references) and a **GitHub Project** board for a cross-cutting status view. We want to offer
that without losing the local Markdown as the source of truth.

Two questions had to be settled before any code: **where** the GitHub capability lives (a new
skill vs. extending `product-item`), and **which backend** it drives (`gh` CLI vs. the official
GitHub MCP server). A survey of the current environment found **no existing skill** that manages
Issues/Projects (`pr-review-toolkit` / `code-review` are PR-review only), so this is net-new; the
realistic building blocks are the `gh` CLI (commonly installed and pre-authenticated) and the
GitHub MCP server. The full design is in
[`docs/design/github-backlog-sync.md`](../design/github-backlog-sync.md).

## Decision

- Build GitHub sync as a **separate sibling skill** named `github-backlog-sync`, not as a
  feature of `product-item`.
- Keep the **local Markdown artifact as the source of truth**; the GitHub Issue is a mirror with
  a backlink, and sync is made **idempotent** by recording `github_issue` / `github_project_item`
  in the artifact frontmatter.
- Target **both backends** behind a single `IssueBackend` interface with a `gh`-CLI adapter
  (default) and a GitHub-MCP adapter, chosen by a Factory at run time.
- Emit an **advisory-only** recommendation to adopt GitHub tracking once the backlog crosses a
  size/complexity threshold (roughly: >15–20 open items, >1 active Epic, >1 contributor,
  multi-sprint, or external stakeholders); a Project board specifically once there is >1 Epic.
- This ADR records the decision; **implementation is deferred** to a later change.

## Why

- **Separate skill (separation of concerns).** Keeps `product-item` offline, deterministic, and
  network-free — its whole value is being a safe, side-effect-light local scaffolder. Folding in
  GitHub/auth/network code would widen its blast radius and couple two very different failure
  modes. A sibling skill can be installed/adopted independently and cross-links back via
  `[[product-item]]`.
- **Local source of truth.** The backlog stays versioned with the code and works with zero
  external dependencies; GitHub becomes an optional projection, not a hard dependency. Recording
  the Issue number in frontmatter reuses the "record the id, never duplicate" pattern the
  scaffolder already applies to parent/roadmap links, so sync is safely re-runnable.
- **Both backends.** Neither backend is universal: some environments have `gh` set up and
  nothing else; others standardize on MCP. An Adapter interface with a Factory lets the sync
  logic be written once and unit-tested against a fake backend, and lets a third backend be added
  later without touching that logic (Adapter + Factory, per the repo's design-pattern
  conventions).
- **Advisory metric.** The counts are cheap (the validator already walks `docs/product/**`), and
  keeping the nudge advisory-only means the offline workflow is never blocked by a
  recommendation.

## Consequences

- A future change adds `skills/github-backlog-sync/` (SKILL.md + a `sync_github_items.py` script +
  an Issue-body template), a README table row, a CHANGELOG entry, and a version bump — following
  the same "adding a skill" checklist used here.
- `product-item` artifacts gain two **optional** frontmatter fields (`github_issue`,
  `github_project_item`); the integrity gate must treat them as optional so unsynced artifacts
  still pass.
- One-way sync (local → GitHub) ships first; read-back from GitHub is explicitly out of scope for
  the initial version and can be revisited.
- If the environment offers neither `gh` nor an MCP backend, the skill no-ops with a clear
  message rather than failing hard.
