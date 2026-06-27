# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `decision-record` skill — scaffolds the next-numbered ADR in `docs/decisions/` from a
  fixed template, with gap-safe numbering and overwrite protection.
- `changelog` skill — adds Keep a Changelog entries under `[Unreleased]`, reusing the
  correct `### <Type>` subsection without creating duplicate headings.
- Markdown linting via `markdownlint-cli2` (`.markdownlint-cli2.jsonc`) and `npm run lint`.
- Manifest and skill-frontmatter invariant tests via `node:test`
  (`test/manifests.test.mjs`), including a `plugin.json` ↔ `marketplace.json` version-sync
  check.
- Pre-commit hook (`.githooks/pre-commit`) and a GitHub Actions CI workflow that run lint
  and tests.
- `CHANGELOG.md` (this file) and `docs/decisions/0001-*.md` recording the tooling decision.
