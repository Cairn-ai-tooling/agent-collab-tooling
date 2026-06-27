---
name: code-review-exchange
description: Use when one agent asks another to review code, or when an agent reviews work produced by another agent — standardizes the review request (scope, diff, concerns) and the review response (severity-tagged findings, clear verdict) so review handoffs are consistent and actionable.
when_to_use: When requesting review of completed work before merge, when handing code to a reviewing agent, or when you are the reviewer responding to another agent's work. Pairs with agent-handoff for the surrounding context.
---

# Code Review Exchange

A review is only useful if the requester knows what was checked and the reviewer knows
what to check. Freeform "can you look at this?" wastes both sides: the reviewer guesses at
scope, the requester gets vague findings. This skill fixes the shape of both halves of the
exchange.

## Part 1 — Requesting a review

Produce a **review request** with these fields. Keep it tight; link to a handoff
(`[[agent-handoff]]`) for deep context rather than duplicating it.

```markdown
# Review request: <title>

## Scope
What to review and what to skip. "Review the new auth middleware; the existing user model
is out of scope."

## What changed
The diff or the exact files/commits to review (e.g. `git diff main`, or list paths).
Point at concrete changes — don't make the reviewer hunt.

## Intent
What this code is supposed to do, so the reviewer can judge correctness against intent,
not just style.

## Concerns / focus areas
Where you're unsure and most want eyes: "I'm not confident the token refresh handles
expiry races." Naming your own doubts gets the highest-value review.

## How to verify
The command(s) to run tests / reproduce behavior, so the reviewer can check, not just read.
```

## Part 2 — Responding to a review

Review against intent and correctness first, style second. Report findings with explicit
**severity** so the requester knows what's blocking versus optional.

### Severity tags (required on every finding)

- **`[blocker]`** — must fix before merge. Bugs, security issues, data loss, broken
  behavior, missing critical tests.
- **`[major]`** — should fix; real problem but not merge-blocking on its own.
- **`[minor]`** — worth fixing: clarity, naming, small inefficiencies.
- **`[nit]`** — optional/stylistic; the requester can ignore freely.
- **`[question]`** — you need an answer to judge; not yet a finding.

### Response format

```markdown
# Review: <title>

## Verdict
One of: **Approve** / **Approve with comments** / **Request changes**.
State it first — the requester needs the bottom line up front.

## Findings
- `[blocker]` `path/file.ts:42` — <what's wrong> → <why it matters> → <suggested fix>.
- `[minor]` `path/other.ts:10` — <observation> → <suggestion>.
- `[question]` <what you need clarified>.

## What I verified
What you actually ran/checked (tests, manual repro) vs. what you only read. Be honest —
"read only, did not run tests" is a valid and important statement.
```

### Reviewer discipline

- **Every finding is actionable.** State the problem, why it matters, and a concrete
  suggested direction. "This is bad" is not a review.
- **Separate fact from preference.** A `[blocker]` must be defensible as a real defect, not
  a style opinion. Tag opinions as `[nit]`.
- **Verify before asserting correctness.** If you claim something is broken, show how it
  breaks. If you didn't run it, say so under "What I verified".
- **Don't rewrite; recommend.** Point to the fix; let the author apply it unless asked.

## Part 3 — Receiving the review back

When you get findings, do not perform agreement or blindly apply suggestions. Evaluate each
on technical merit, push back where a finding is wrong (with reasoning), and fix what's
real. Address every `[blocker]` before merge. This mirrors `[[receiving-code-review]]`:
verification and honest reasoning over reflexive compliance.
