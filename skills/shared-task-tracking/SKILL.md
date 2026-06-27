---
name: shared-task-tracking
description: Use when multiple agents work toward a shared goal and need a single source of truth for tasks — defines where the shared task list lives, how to claim/update/complete items, and conventions that prevent double-work and dropped tasks.
when_to_use: When coordinating work across multiple agents or sessions on the same project, when splitting a large effort into parallel tasks, or whenever you need to know "who is doing what" without asking.
---

# Shared Task Tracking

When two agents pick up the same task, one of them wasted their work. When a task has no
owner, it gets dropped. A shared task list exists to make ownership and status
unambiguous at a glance — not to be a perfect project plan.

## Where the list lives

Use a single, committed file at the repo root: **`TASKS.md`**. It is version-controlled so
the history of who-did-what is preserved, and it travels with the code. One file, one
source of truth. Do not keep parallel lists in chat, scratch files, or memory.

If the project already has a task system (an issue tracker, an existing `TODO.md`), use
that instead of creating a competing one — surface it rather than fragmenting state.

## Task format

Each task is a checklist line with an explicit status, owner, and stable id:

```markdown
## Tasks

- [ ] `T1` **(open)** Add rate limiting to the public API — _unassigned_
- [~] `T2` **(in-progress, @agent-b)** Migrate auth to JWT — started 2026-06-27
- [x] `T3` **(done, @agent-a)** Write integration tests for /login
- [!] `T4` **(blocked, @agent-c)** Deploy preview — needs staging credentials
```

Status legend (keep this legend at the top of `TASKS.md`):
- `[ ]` **open** — available to claim, no owner.
- `[~]` **in-progress** — actively owned; the owner tag is mandatory.
- `[x]` **done** — completed and verified.
- `[!]` **blocked** — cannot proceed; the line must state what unblocks it.

## The protocol

1. **Before starting work, claim a task.** Change `[ ]` → `[~]`, add your owner tag, and
   write the change to `TASKS.md` *first* — before you begin. Claiming is what prevents
   collisions, so it must happen up front, not after.
2. **One in-progress task per agent** by default. Finish or release before claiming
   another, so ownership stays legible.
3. **Never silently take an owned task.** If a task is `[~]` with another owner, leave it.
   If you believe it's stalled, note it and coordinate (see `[[agent-handoff]]`).
4. **Mark done only when verified.** `[x]` means the work is complete *and* checked —
   tests run, behavior confirmed (see `[[verification-before-completion]]`). Don't mark
   done on "should work".
5. **Blocked tasks state their blocker.** `[!]` is useless without "needs X". The blocker
   line is a request for help, so make it actionable.
6. **Add new tasks as you discover them.** Give each a fresh id (`T5`, `T6`, …); ids are
   never reused, so references stay stable.

## Avoiding double-work

- Read `TASKS.md` immediately before claiming — your local view may be stale.
- Claim atomically: update the file and treat that write as the lock. If two agents race,
  the second to write should yield and pick a different task.
- Keep tasks small enough that one agent finishes one in a session — large tasks hide
  progress and invite overlap. Split when in doubt.

## Relationship to per-session todos

This is the *cross-agent* shared list. An individual agent's in-session todo list (its own
working checklist) is separate and ephemeral — don't conflate them. Promote a working item
to `TASKS.md` only when it's work another agent might pick up.
