---
name: decision-record
description: Use when recording an architecture/design decision — scaffolds the next-numbered ADR in docs/decisions/ from the project's template and cross-links it.
when_to_use: When a non-obvious architectural or design choice is made (a tradeoff, a tool adoption, a convention) that future readers will want the rationale for. Not for trivial or easily-reversible choices.
---

# Decision Record (ADR)

An ADR captures *why* a decision was made so nobody has to re-derive or re-litigate it
later. Record the decision and its rejected alternatives — the alternatives are often the
most valuable part, because they stop the same debate from recurring.

This skill is **portable**: it discovers paths instead of assuming them, and it is
**idempotent** — re-running never reuses or overwrites a number.

## Inputs

- **Decisions directory** — default `docs/decisions/`. Accept an override argument
  (e.g. `decision-record dir=architecture/adr`). If the default is absent and no override
  is given, ask whether to create `docs/decisions/`.
- **Fields** — gather from the invocation args/context; only ask for what's missing, and
  ask concisely:
  - **Title** (required)
  - **Status** — default `Accepted`; allow `Proposed`
  - **Context** (required) — why the decision is needed
  - **Decision** (required) — what was decided
  - **Why** — rationale, including `Why not <alternative>` where relevant
  - **Consequences** — follow-ups, tradeoffs, what this enables or constrains

Never invent content for a required field. If it's missing, ask — briefly.

## Procedure

1. **Locate the directory.** Use the override if given, else `docs/decisions/`. If it
   doesn't exist, create it (after confirming, unless an override path was explicitly
   passed).
2. **Compute the next number.** Scan for files matching `NNNN-*.md`, take the **maximum**
   4-digit prefix, add 1, zero-pad to 4 digits. **Handle gaps with max+1 — never reuse a
   number even if earlier ones are missing.** If no ADRs exist, start at `0001`.
3. **Build the slug.** Kebab-case the title (lowercase, spaces/punctuation → single
   hyphens, trim). Filename = `NNNN-<slug>.md`.
4. **Guard against collisions.**
   - If `NNNN-<slug>.md` already exists, **refuse to overwrite** — stop and report.
   - If a *different-numbered* file with a near-identical slug exists, **warn** (possible
     duplicate decision) and ask whether to continue.
5. **Write the file** using EXACTLY this template (wrap prose at ~100 columns):

   ```markdown
   # NNNN — <Title>

   **Status:** <Status>

   ## Context

   <why this decision is needed>

   ## Decision

   <what was decided — bullet points are fine>

   ## Why

   <rationale; include "Why not <alternative>" where relevant>

   ## Consequences

   <follow-ups, trade-offs, what this enables or constrains>
   ```

   Keep a blank line after each heading and around any list so the file passes common
   Markdown linters (markdownlint MD022/MD032).

6. **Offer to cross-link** (only if the target files already exist — never create them
   just to link):
   - `docs/roadmap.md` — add a one-line pointer to the new ADR.
   - the relevant entry in `docs/pain-points.md` — add a one-line pointer.
   - **Never duplicate an existing link** — check before adding.
7. **Print the created file path.** Do **not** commit — leave that to the user.

## Acceptance checklist

- Numbering: with `0001`, `0002` present → next is `0003`. With `0001`, `0003` present
  (gap) → next is `0004` (max+1), **not** `0002`. Empty dir → `0001`.
- Re-running with the same title does **not** overwrite; it refuses and reports.
- The written file matches the template headings exactly.
- Cross-links are added only to pre-existing files and are never duplicated.

Related: pairs with `[[changelog]]` when a decision also ships a user-facing change.
