---
id: TASK-NNN
title: <short title>
type: task
status: Proposed        # Proposed | Ready | In Progress | In Review | Done | Archived
owner: <name>
created: YYYY-MM-DD
story: STORY-NNN        # parent story (or "none" for a standalone task/chore/bug)
plan: <PLAN-NNN or none>
---

# TASK-NNN — <Title>

## Description

<What this task does, concretely. One paragraph.>

## Acceptance criteria

- [ ] <verifiable condition>
- [ ] <verifiable condition>

## Definition of done

- [ ] Tests written first (TDD) and passing — `uv run pytest` / `npm test` as applicable.
- [ ] `uv run pre-commit run --all-files` clean.
- [ ] CHANGELOG entry added if user-facing or notable.
- [ ] ADR written if a non-obvious architectural choice was made.
- [ ] **Closure check** — before calling this done:
  - [ ] **Converged** — the end state is more ordered than the start (one source of truth).
  - [ ] **Legible** — the result maps 1:1 to the stated intent, no "sort of".
  - [ ] **Closed** — verified by running something, not asserted.
  - [ ] **Edges surfaced** — remaining rough bits are named here, not hidden.

## Parent story

STORY-NNN — <title>  (or "standalone" for a chore/bug)

## Links

- Implementation plan: <PLAN-NNN / link, or none>
- Related: <roadmap item, PR, ADR>
