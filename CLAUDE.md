# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A centralized **Claude Code plugin** that bundles reusable *agent-collaboration skills*.
There is no application code, build step, or test runner — the deliverable is the skills
themselves plus the two manifests that make them installable. Other projects consume this
repo via the plugin marketplace rather than copying files.

## Architecture

The repo is simultaneously a **plugin** and its own **marketplace catalog**:

- `.claude-plugin/plugin.json` — the plugin manifest. `name` is the only required field;
  `skills: "./skills/"` points at the skill directory. Bump `version` on every released
  change.
- `.claude-plugin/marketplace.json` — the catalog. Its `plugins` array contains a single
  entry whose `source` is `"."` — i.e. the plugin *is* this repo root. This is what lets
  another project run `/plugin marketplace add cairn-ai-tooling/agent-collab-tooling` and then
  `/plugin install agent-collab-tooling@cairn-ai-agent-tooling`.
- `skills/<name>/SKILL.md` — one directory per skill, auto-discovered at install time.

The two manifests are coupled: the plugin `name`, `version`, and the marketplace plugin
entry must stay in sync. When you change one, check the other.

## Skill authoring conventions

Every skill is a `skills/<kebab-case-name>/SKILL.md` with YAML frontmatter:

- `name` (kebab-case, matches the directory), `description`, and `when_to_use` are the
  fields used here. The `description` is what drives auto-invocation — make it precise about
  *when* the skill applies, not just what it does.
- Skill bodies are **actionable agent instructions**, not placeholders: state the rule,
  show the exact format/template, and give quality checks the agent can self-apply.
- Cross-link related skills with `[[skill-name]]` (including superpowers skills like
  `[[verification-before-completion]]` and `[[receiving-code-review]]`). These three seed
  skills deliberately reference each other and the superpowers set.

When adding a skill: create the directory + `SKILL.md`, add a row to the README's "Skills
in this plugin" table, add a `CHANGELOG.md` `[Unreleased]` entry, and (on release) bump
`version` in both manifests.

## Commands

```bash
npm install        # installs markdownlint-cli2 and enables the .githooks pre-commit hook
npm run lint       # markdownlint over all Markdown (config in .markdownlint-cli2.jsonc)
npm run lint:fix   # auto-fix fixable lint issues
npm run test:node  # node:test — runs test/manifests.test.mjs
npm run test:py    # uv run pytest — tests skills' bundled Python scripts (needs uv)
npm test           # both suites (node + Python)
npm run check      # lint + test together (what CI and the pre-commit hook run)
```

Run a single node test by name: `node --test --test-name-pattern "version-synced"`.
Run a single Python test: `uv run pytest tests/product_item -k yaml_title`.
`uv` is required for the Python tests (it manages an isolated `.venv`) and matches the
`uv run` convention the skills use to invoke their scripts.

## Validating changes

`test/manifests.test.mjs` (node:test) enforces the manifest/skill invariants that are easy to
break by hand:

- `plugin.json` and `marketplace.json` must stay **version-synced** (same version for the
  plugin entry) — this is the most important check, since the two manifests are coupled.
- every `skills/<name>/SKILL.md` must have frontmatter with `name` + `description`, and
  `name` must match its directory.

`tests/` (pytest, run via `uv`) covers the Python scripts skills bundle — e.g. the
`product-item` scaffolder/validator: YAML-safe titles, gap-safe numbering, the `--with-plan`
cross-wiring, and drift parity between the scaffolder and the integrity gate. New Python helper
scripts should ship with tests here; import them via the `sys.path` shim in `tests/conftest.py`
(the scripts are skill *assets*, not an installed package).

There is no type checking — there is no typed source; these tests are the equivalent
guardrail. Both lint and tests run via the pre-commit hook and GitHub Actions
(`.github/workflows/ci.yml`). To smoke-test plugin discovery locally from a clone:

```bash
/plugin marketplace add /path/to/this/repo
/plugin install agent-collab-tooling@cairn-ai-agent-tooling
```

## Records & conventions

- **ADRs** live in `docs/decisions/NNNN-*.md` (4-digit, gap-safe numbering). Record
  non-trivial decisions with the `decision-record` skill; rationale for the tooling is in
  `docs/decisions/0001-adopt-linting-tests-and-records.md`.
- **CHANGELOG.md** follows Keep a Changelog 1.1.0 + SemVer. Add changes under
  `[Unreleased]` with the `changelog` skill (never create a duplicate `### <Type>` heading).

## Notes

- `.remember/` and `node_modules/` are gitignored — never commit them.
- This is a plugin *source* repo, not a project that gets deployed; ignore the Vercel/AWS
  session tooling unless explicitly asked.
