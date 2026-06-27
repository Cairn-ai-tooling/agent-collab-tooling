# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-27

### Added

- Packaged as an installable Claude Code plugin and self-hosted marketplace catalog
  (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`).
- `agent-handoff` skill — structured handoff (goal, decisions, state, remaining work,
  blockers) for passing work between agents or sessions.
- `shared-task-tracking` skill — a single `TASKS.md` source of truth with a
  claim/update/complete protocol that prevents double-work.
- `code-review-exchange` skill — a standardized review request plus a severity-tagged
  review response and verdict.
- `decision-record` skill — scaffolds the next-numbered ADR in `docs/decisions/` from a
  fixed template, with gap-safe numbering and overwrite protection.
- `changelog` skill — adds Keep a Changelog entries under `[Unreleased]`, reusing the
  correct `### <Type>` subsection without creating duplicate headings.
- Markdown linting via `markdownlint-cli2` (`.markdownlint-cli2.jsonc`).
- Manifest and skill-frontmatter invariant tests via `node:test`
  (`test/manifests.test.mjs`), including a `plugin.json` ↔ `marketplace.json` version-sync
  check.
- Pre-commit hook (`.githooks/pre-commit`) and a GitHub Actions CI workflow that run lint
  and tests.
- Architecture Decision Records in `docs/decisions/` (`0001` tooling adoption, `0002`
  linter/advisory decision).

### Security

- The dev-only Markdown linter carries two residual moderate quadratic-DoS advisories in
  transitive dependencies (`js-yaml`, `markdown-it`). Accepted as non-exploitable on this
  repo's trusted input rather than forced via `npm audit fix --force` (which downgrades the
  linter); see `docs/decisions/0002-*.md`.

[Unreleased]: https://github.com/cairn-ai-tooling/agent-collab-tooling/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/cairn-ai-tooling/agent-collab-tooling/releases/tag/v0.1.0
