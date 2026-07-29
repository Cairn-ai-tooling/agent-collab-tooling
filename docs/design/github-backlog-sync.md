# Design — `github-backlog-sync` (GitHub Issues / Projects sync for `product-item`)

**Status:** Proposed (design only — no implementation this round)
**Related:** [`product-item`](../../skills/product-item/SKILL.md),
[`shared-task-tracking`](../../skills/shared-task-tracking/SKILL.md), ADR
[`0003`](../decisions/0003-github-backlog-sync-skill.md)

## Context

The `product-item` skill scaffolds a local, file-based backlog under `docs/product/`
(Epics → Stories → Tasks → Plans). That is ideal for small efforts and for keeping the backlog
versioned next to the code. But once a project grows — more contributors, more concurrent work,
external stakeholders who want visibility — a Markdown backlog stops being enough: people expect
**GitHub Issues** (assignment, comments, cross-references from commits/PRs) and a **GitHub
Project** board for a cross-cutting status/roadmap view.

We want a way to **push tracked items outward to GitHub** without abandoning the local artifacts
as the source of truth, plus a **metric** so the tooling only recommends this once a project is
big enough to warrant it.

## Goals

- Mirror local `product-item` artifacts to GitHub Issues, and optionally onto a GitHub Project.
- Keep the local Markdown as the **source of truth**; the Issue is a mirror with a backlink.
- Make sync **idempotent** — re-running never duplicates Issues.
- Keep `product-item` itself **offline and deterministic** — no network/auth code leaks into the
  scaffolder.
- Support **either** the `gh` CLI **or** the GitHub MCP server as the backend.
- Emit an **advisory** recommending GitHub tracking only past a size threshold.

## Non-goals

- Two-way sync / pulling GitHub edits back into Markdown (future; start one-way local → GitHub).
- Replacing `shared-task-tracking` (that stays the *session-local* coordination surface; this is
  *persistent, external* tracking — they complement, they don't compete).
- Bundling or configuring a GitHub MCP server for the consumer.

## Prior art

- **No existing skill** in this plugin (or the surveyed environment) manages GitHub Issues or
  Projects. `pr-review-toolkit` / `code-review` are pull-request *review* tools, not backlog
  tools — no reuse there.
- **`gh` CLI** is broadly available and, where present, already authenticated. `gh issue …`
  covers Issues; `gh project …` covers Projects v2 (via GraphQL under the hood).
- **Official GitHub MCP server** offers typed, programmatic access to the same surface for
  consumers who prefer an MCP integration over shelling out.

Because both backends exist and neither is universal, the design targets **both** behind one
interface rather than hard-coding a single tool.

## Decision summary

Build a **separate sibling skill** — `github-backlog-sync` — that reads `docs/product/**` and
mirrors artifacts to GitHub. `product-item` is unchanged. See ADR
[`0003`](../decisions/0003-github-backlog-sync-skill.md) for the rationale and the shape/backend
trade-offs considered.

## Architecture

### Source of truth and idempotency

The local artifact stays authoritative. Sync state is recorded **in the artifact frontmatter** so
the next run knows what already exists (the same "record the id, never duplicate" pattern
`product-item` already uses for parent/roadmap links):

```text
github_issue: 42                 # the mirrored Issue number (absent = not yet synced)
github_project_item: PVTI_xxx    # the Project item node id (absent = not on the board)
```

Sync algorithm per artifact:

```text
if github_issue is absent:
    create the Issue  ->  record its number back into the artifact frontmatter
else:
    update the existing Issue (title / body / labels / state)
if a Project is configured and github_project_item is absent:
    add the Issue to the Project  ->  record the item node id
set the Project status field from the artifact's status
```

Creating an Issue is the only step that writes back to the local file (recording the number);
everything else is derived, so a re-run with no local changes is a no-op.

### Status mapping

The artifact lifecycle maps to a GitHub Project **single-select** status field, and drives
Issue open/closed state:

```text
Proposed    -> Project "Proposed"     (Issue open)
Ready       -> Project "Ready"        (Issue open)
In Progress -> Project "In Progress"  (Issue open)
In Review   -> Project "In Review"    (Issue open)
Done        -> Project "Done"         (Issue closed)
Archived    -> Project "Archived"     (Issue closed)
```

Type (`epic` / `story` / `task` / `plan`) maps to an Issue **label**; parent/child links become a
task-list / cross-reference in the Issue body so the hierarchy is legible on GitHub too.

### Backend adapter (design for both)

One interface, two adapters, selected by a Factory at run time (prefer an explicitly configured
backend; otherwise pick `gh` if it is installed and authenticated, else MCP if available):

```text
IssueBackend (interface)
  ensure_issue(artifact)        -> issue_number      # create if missing, else update
  set_issue_state(number, open) -> None
  ensure_project_item(number)   -> project_item_id   # add to board if missing
  set_project_status(item_id, status) -> None

GhCliBackend      -> wraps `gh issue` / `gh project` (default; zero-config where gh is set up)
GitHubMcpBackend  -> wraps the official GitHub MCP server tools (typed/programmatic)
```

Only the adapters touch GitHub. The sync loop is written once against `IssueBackend`, so adding a
third backend later (e.g. a REST client) never touches the sync logic — the Adapter + Factory
patterns keep the network edge isolated (and unit-testable with a fake backend).

## The recommendation metric

Local Markdown is enough for small backlogs. The tooling should **recommend** graduating to
GitHub Issues/Projects only when the backlog crosses a size/complexity threshold — recommend when
**any** of these hold:

- more than ~**15–20 open** tracked artifacts, or
- more than **1 active Epic**, or
- more than **1 person/agent** working the backlog (shared external visibility needed), or
- the work **spans multiple sprints** / more than ~2 weeks, or
- **external stakeholders** need read access.

Use a **GitHub Project (board)** specifically once there is **more than 1 Epic** and a
cross-cutting status view is wanted; below that, plain Issues (or staying local) suffice.

These counts are cheap to compute — the validator already walks `docs/product/**` — so the
advisory can be emitted automatically. Proposed surface: a **non-failing** advisory line from
`validate_product_items.py` (or the `product-item` closing report), e.g.
`note: 23 open items across 3 epics — consider /github-backlog-sync to mirror to GitHub Issues.`
It stays advisory (never an error) so it never blocks the offline workflow.

## Proposed skill shape

```text
skills/github-backlog-sync/
  SKILL.md
  assets/
    scripts/
      sync_github_items.py     # reads docs/product/**, drives an IssueBackend
    templates/
      issue-body-template.md   # how an artifact renders into an Issue body
```

Procedure sketch (SKILL.md): resolve the backend → dry-run diff (what would be created/updated) →
confirm with the user → sync → write back any new `github_issue` / `github_project_item` values →
report. Confirm-before-write and "print the diff first" mirror `product-item`'s existing
with-confirm ethos, since this reaches an external system.

## Open questions

- Whether to fold this under a `github/` skill namespace if more GitHub skills appear later
  (the name `github-backlog-sync` is settled — see ADR 0003).
- Labels/Project field names: assume-and-create, or require the consumer to pre-create them?
- Where exactly the advisory lives (validator vs skill report) and whether it is opt-out.
- Whether/when to add read-back (GitHub → Markdown) for status changes made on the board.

## Verification (when built)

- Unit-test the sync loop against a **fake `IssueBackend`** (no network): create-then-update is
  idempotent; status→state mapping is correct; missing frontmatter triggers create, present
  triggers update.
- Integration smoke against a throwaway repo with the `gh` adapter: run twice, assert the second
  run creates nothing new and the frontmatter carries stable ids.
