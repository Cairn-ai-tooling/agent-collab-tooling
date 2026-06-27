---
name: agent-handoff
description: Use when finishing a chunk of work that another agent (or a future session) will continue — produces a structured handoff capturing goal, decisions, current state, remaining work, and blockers so the next agent can resume without re-deriving context.
when_to_use: At the end of a work session, when passing a task to another agent, when context is about to be summarized/compacted, or whenever you say "handing this off" or "picking up where X left off".
---

# Agent Handoff

A handoff fails when the next agent has to reconstruct what you already knew. The cost of
a bad handoff is paid by someone else, later, with less context. Your job is to make the
next agent productive in their first action, not their tenth.

## When to produce a handoff

- You are ending a session with work unfinished.
- You are delegating a sub-task to another agent.
- Context is about to be compacted and you want a durable record.
- The user explicitly asks you to "hand off", "write up state", or "prepare for the next agent".

## The rule

**Write the handoff for someone with zero conversation history.** Do not reference "the
file we discussed" or "the bug from earlier" — name the file, restate the bug. If the next
agent would have to ask a clarifying question to act, answer it in the handoff.

## Handoff template

Produce a single Markdown document with exactly these sections, in this order. Omit a
section only if it is genuinely empty (e.g. no blockers) — and say so explicitly rather
than dropping the heading silently.

```markdown
# Handoff: <one-line task title>

## Goal
What we are ultimately trying to achieve and why (the user-facing outcome, 1–3 sentences).

## Current state
What is true *right now*: branch name, what runs/passes, what is half-finished.
Be concrete — "auth middleware compiles and unit tests pass; integration test not written".

## Decisions made (and why)
- <decision> — <rationale>. Include rejected alternatives if they'll otherwise be re-litigated.

## Done
- <completed item> (file:line where relevant)

## Remaining work
Ordered by what to do next. Each item actionable on its own:
1. <next action> — <where / how>
2. ...

## Blockers / open questions
- <blocker> — what's needed to unblock (a credential, a decision from the user, an answer).
- State "None known" if there are none.

## Key files & entry points
- `path/to/file.ext:line` — what it is / why it matters.
```

## Quality checks before you hand off

1. **No dangling references.** Search your own handoff for "the", "that", "earlier",
   "we discussed" — every one must resolve without conversation history.
2. **Next action is unambiguous.** The first item under "Remaining work" should be
   executable immediately, not "figure out what to do".
3. **State is verified, not assumed.** If you claim tests pass, you ran them. If you're
   unsure, write "untested" rather than implying success. (See `[[verification-before-completion]]`.)
4. **Blockers are explicit.** A silent blocker becomes the next agent's wasted hour.

## Receiving a handoff

When you *pick up* a handoff:
- Read it fully before acting.
- Re-verify any claimed state you depend on (run the tests, check the branch) rather than
  trusting it blind — handoffs reflect what was true when written.
- If a decision in the handoff looks wrong, raise it; don't silently override (see
  `[[receiving-code-review]]` for the mindset).
