---
name: changelog
description: Use when recording a notable change — adds a correctly-placed entry under [Unreleased] in CHANGELOG.md (Keep a Changelog format), reusing the right ### section without duplicating headings.
when_to_use: Right after making a user-facing or notable change (feature, fix, removal, security patch) that should appear in release notes. Run once per change; safe to run repeatedly.
---

# Changelog

Maintains `CHANGELOG.md` in [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) 1.1.0
format with [SemVer](https://semver.org/). Changes accumulate under `## [Unreleased]` and
are cut into a version at release time (not by this skill).

The single most common bug this skill must avoid: **creating a second `### <Type>` heading
when one already exists.** Always append to the existing subsection.

## Inputs

- **Entry text** — what changed, user-facing, concise (include *why* when it isn't obvious).
- **Change type** — one of: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`,
  `Security`. Infer from the entry; ask only if genuinely ambiguous.

## Canonical section order

`### Added` → `### Changed` → `### Deprecated` → `### Removed` → `### Fixed` → `### Security`

When creating a missing subsection, insert it so the subsections stay in this order.

## Procedure

1. **Locate `CHANGELOG.md`** at the repo root. If missing, scaffold it:

   ```markdown
   # Changelog

   All notable changes to this project are documented in this file.

   The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
   and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

   ## [Unreleased]
   ```

2. **Sanity-check the shape.** If the file exists but is clearly **not** Keep-a-Changelog
   shaped (no `# Changelog` / no `## [` version headings), **report and stop** — do not
   mangle an unrecognized file.
3. **Ensure `## [Unreleased]` exists.** If absent, create it directly under the header
   block, above the most recent released version section.
4. **Find or create the `### <Type>` subsection** *within* `[Unreleased]`:
   - If a `### <Type>` heading already exists under `[Unreleased]`, **use it** — do not
     add another. (This is the critical rule.)
   - If it doesn't exist, create it in the canonical order above, with a blank line after
     the heading (markdownlint MD022/MD032).
   - Scope the search to the `[Unreleased]` section only — a `### Added` under an older
     released version is unrelated and must be left alone.
5. **Append the entry** as a new `-` list bullet at the **end** of that subsection. Wrap at ~100
   columns; indent continuation lines to align under the text (hanging indent).
6. **Leave released version sections untouched.** Do **not** commit — leave that to the user.

## Worked example

Given:

```markdown
## [Unreleased]

### Added

- New decision-record skill.
```

Running with entry "changelog skill" / type `Added` must produce (one `### Added`, two
bullets) — **not** a duplicate heading:

```markdown
## [Unreleased]

### Added

- New decision-record skill.
- New changelog skill.
```

Running with entry "fix numbering gap handling" / type `Fixed` adds a new subsection in
canonical order (Fixed comes after Added):

```markdown
## [Unreleased]

### Added

- New decision-record skill.
- New changelog skill.

### Fixed

- Fix numbering gap handling.
```

## Acceptance checklist

- Appending to an existing `### Added` adds a bullet and leaves a **single** `### Added`
  heading (no duplicate).
- A missing subsection is created in canonical order (e.g. `Fixed` after `Added`).
- A `### Added` under a released version is never confused with the one under `[Unreleased]`.
- Re-running is idempotent in shape: it never creates duplicate `### <Type>` headings.
- A non-Keep-a-Changelog file is reported, not rewritten.

Related: pairs with `[[decision-record]]` when a change also warrants recording its rationale.
