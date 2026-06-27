# 0001 — Adopt linting, manifest tests, and decision/changelog records

**Status:** Accepted

## Context

This repository is a Claude Code plugin made up almost entirely of Markdown skills plus
two coupled JSON manifests (`plugin.json` and `marketplace.json`). It has no application
code, so traditional unit testing and type checking do not apply. We still want automated
guardrails: consistent Markdown style, protection against the manifests drifting out of
sync, and a durable record of versioned changes and the decisions behind them.

## Decision

- Lint Markdown with **markdownlint-cli2**, configured in `.markdownlint-cli2.jsonc`
  (line-length off; `MD024` set to `siblings_only` so Keep a Changelog can repeat
  `### Added` across versions; `MD041` off because skills open with YAML frontmatter).
- Validate the manifests and skill frontmatter with the built-in **`node:test`** runner
  (`test/manifests.test.mjs`) — no extra test dependency. The key invariant is that
  `plugin.json` and the matching `marketplace.json` plugin entry share the same version.
- Gate locally with a **git pre-commit hook** (`.githooks/pre-commit`, enabled by the
  `prepare` npm script) and in CI with **GitHub Actions** (`.github/workflows/ci.yml`).
- Track versions with a **CHANGELOG.md** in Keep a Changelog 1.1.0 format using SemVer.
- Record non-trivial decisions as **ADRs** under `docs/decisions/NNNN-*.md`.

## Why

- markdownlint-cli2 is the de-facto standard and matches the rules the editor already
  surfaces, so contributors see consistent feedback. Why not a Python linter (pymarkdown):
  the repo already needs Node for nothing else, but markdownlint's rule set and ecosystem
  are richer and the single dev dependency is cheap.
- `node:test` avoids pulling in a framework (Jest/Vitest) for what is a handful of
  invariant checks. The version-sync assertion exists because the two manifests are the
  one place a silent, easy-to-miss inconsistency can ship.
- Pre-commit catches problems before they are committed; CI catches them for any
  contributor whose hook isn't installed. The two are complementary, not redundant.
- Keep a Changelog + SemVer and ADRs are low-cost, high-recall ways to answer "what
  changed?" and "why did we do it this way?" — and they are dogfooded by this repo's own
  `changelog` and `decision-record` skills.

## Consequences

- Contributors run `npm install` once to enable the hook and linter; CI enforces the same
  checks regardless.
- Adding or renaming a skill now means: update both manifests (kept in sync by the test),
  add a CHANGELOG `[Unreleased]` entry, and add the skill to the README table.
- Type checking is intentionally out of scope while there is no typed source; if scripts or
  typed code are added later, revisit this decision.
