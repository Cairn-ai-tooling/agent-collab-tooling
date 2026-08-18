# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `close-out-sweep` skill — batch-retires completed Epics from a `docs/product/` backlog:
  `git mv`s each `Done` Epic's whole subtree (stories/tasks/plan, resolved via frontmatter links)
  into per-type `archive/` dirs, regenerates the shipped index, and prunes the Epic's roadmap row.
  Plan-only by default with a confirm-first `--apply`; idempotent (nothing `Done` = no-op). The
  batch counterpart to `product-item`.
- `product-item` gains `generate_shipped_index.py` — derives `docs/product/shipped.md` from `Done`
  epics (recursing `epics/archive/`), sorted, with an empty-state placeholder. Never hand-edited.

### Changed

- `product-item` scanners are now **archive-aware**: `next_id` (`new_product_item.py`) and
  `validate_tree` (`validate_product_items.py`) recurse into `<type>/archive/`, so archived ids
  still count (never reused) and cross-links resolve across the active/archive boundary. The
  skill gains a "closing out shipped work" note cross-linking `close-out-sweep`.

## [0.3.0] - 2026-08-17

### Added

- `github-backlog-sync` skill — mirrors the local `docs/product/` backlog to GitHub Issues and,
  optionally, a GitHub Project board. Idempotent (records `github_issue:` / `github_project_item:`
  back into artifact frontmatter), plan-only by default with a confirm-first `--apply`, and it
  reports backlog counts against a size metric so GitHub is recommended only when it's warranted.
  The sync engine is backend-agnostic (a `gh`-CLI adapter, with an agent-driven GitHub MCP
  fallback documented in the skill) and unit-tested against a fake backend. It also flags unfilled
  **stub** artifacts (offering to fill them via `product-item`) and **status drift** off the
  canonical set, and on a re-sync skips artifacts whose content is unchanged since last sync
  (tracked by a `github_synced_digest:`). Implements the design in
  `docs/design/github-backlog-sync.md` / ADR 0003.

## [0.2.0] - 2026-07-29

### Added

- Python test harness (`uv` + `pytest`, config in `pyproject.toml`, tests under `tests/`) for
  the Python scripts skills bundle, starting with the `product-item` scaffolder and validator
  (YAML-safe titles, gap-safe numbering, `--with-plan` cross-wiring, scaffolder↔validator drift
  guards). Exposed as `npm run test:py`; `npm test` now runs the node and Python suites. Recorded
  in `docs/decisions/0004-adopt-python-tests-uv-pytest.md`.
- `product-item` skill — scaffolds the next-numbered backlog artifact (Epic, User Story, Task,
  Implementation Plan) from `docs/product/templates/`, wiring parent/child links and a roadmap
  pointer. Bundles a self-contained scaffolder and integrity-gate script (`pyyaml` only, no
  application-package import) plus a bootstrap that seeds the workflow into any repo.
- `product-item` scaffolder flags `--status`, `--standalone`, and `--with-plan`, and YAML-safe
  title quoting so a title containing a `#` (e.g. "PR #30") or `:` round-trips instead of being
  truncated as a comment.

### Changed

- `markdownlint-cli2` now ignores the `product-item` scaffold templates and roadmap seed, which
  are placeholder-based data (filled by exact-string substitution) rather than prose.
- CI and the pre-commit hook now require `uv` and run the Python tests alongside lint and the
  node manifest tests.

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

[Unreleased]: https://github.com/cairn-ai-tooling/agent-collab-tooling/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/cairn-ai-tooling/agent-collab-tooling/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/cairn-ai-tooling/agent-collab-tooling/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/cairn-ai-tooling/agent-collab-tooling/releases/tag/v0.1.0
