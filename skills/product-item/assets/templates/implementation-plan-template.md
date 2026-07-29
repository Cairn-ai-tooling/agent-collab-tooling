---
id: PLAN-NNN
title: <short title>
type: implementation-plan
status: Proposed        # Proposed | Ready | In Progress | In Review | Done | Archived
owner: <name>
created: YYYY-MM-DD
covers: <EPIC-NNN | STORY-NNN | TASK-NNN>
---

# PLAN-NNN — <Title>

> Context → Approach → Files → Verification. (Mirrors the `superpowers:writing-plans`
> skill's shape, if that skill is installed.)

## Context

<Why this change is being made — the problem or need it addresses, what prompted it, and the
intended outcome. Link the Epic/Story/Task and any relevant ADR (docs/decisions/) or design doc.>

## Approach

<The recommended approach only (not every alternative). Describe the design, the established
design patterns to apply where they fit (e.g. Factory / Adapter / Strategy), and the existing
shared utilities/modules in this repo to reuse before writing new code.>

## Files to change

<Name the critical files. For a pattern repeated across many files, describe it once and list
a few representative paths.>

- `path/to/file.py` — <what changes>

## Test plan (TDD)

<Failing test first → implement → green. Name the test files and the cases that pin behaviour.>

- `tests/.../test_*.py` — <cases>

## Verification

<How to prove it works end-to-end: commands to run, MCP tools, manual smoke test.>

```bash
uv run pytest tests/... -v
uv run pre-commit run --all-files
```

**Closure check** — before calling the work done: **converged** (end state more ordered than
the start), **legible** (maps 1:1 to the stated intent), **closed** (verified by running
something, not asserted), **edges surfaced** (remaining rough bits named, not hidden).

## Out of scope

<Explicit non-goals, to keep the diff focused.>
