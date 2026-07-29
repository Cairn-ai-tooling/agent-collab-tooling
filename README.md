# Agent Collaboration Tooling

Centralized, reusable tooling for AI agents — packaged as an installable
[Claude Code plugin](https://docs.claude.com/en/docs/claude-code/plugins).

## Why this repository exists

As we work with AI agents across many projects, we keep re-discovering the same
collaboration patterns: how one agent hands work to another, how agents coordinate a shared
task list, how they review each other's code. Re-implementing those patterns in every
project repo clutters them and lets the patterns drift apart.

This repository keeps those collaboration **skills** in one place so that:

- **Project repos stay clean and focused** — they pull in tooling instead of hosting it.
- **Skills evolve once** — improve a skill here and every project gets the update.
- **Agents behave consistently** — the same handoff format, the same review conventions,
  everywhere.

## What is a "skill"?

A skill is a focused, model-readable instruction set that teaches an agent *how* to do
something well. Each skill is a directory under [`skills/`](skills/) containing a
`SKILL.md` with YAML frontmatter (`name`, `description`, `when_to_use`) followed by the
guidance the agent follows. Claude Code auto-discovers them when the plugin is installed.

## Skills in this plugin

| Skill | Use it when… |
| ----- | ------------ |
| [`agent-handoff`](skills/agent-handoff/SKILL.md) | Finishing work that another agent or a future session will continue — produces a structured handoff (goal, decisions, state, remaining work, blockers). |
| [`shared-task-tracking`](skills/shared-task-tracking/SKILL.md) | Multiple agents work toward a shared goal — defines a single `TASKS.md` source of truth and a claim/update/complete protocol that prevents double-work. |
| [`code-review-exchange`](skills/code-review-exchange/SKILL.md) | One agent asks another to review code — standardizes the review request and the severity-tagged review response. |
| [`decision-record`](skills/decision-record/SKILL.md) | Recording an architecture/design decision — scaffolds the next-numbered ADR in `docs/decisions/` from a template, with gap-safe numbering. |
| [`changelog`](skills/changelog/SKILL.md) | Recording a notable change — adds a correctly-placed entry under `[Unreleased]` in `CHANGELOG.md`, reusing the right `### <Type>` section without duplicating headings. |
| [`product-item`](skills/product-item/SKILL.md) | Creating a backlog artifact — scaffolds the next-numbered Epic, User Story, Task, or Implementation Plan from `docs/product/templates/`, wires parent/child links, and adds a roadmap pointer. Self-contained (`pyyaml` only) and bootstraps the workflow into any repo. |

## Installing in another project

This repo is both a plugin **and** its own marketplace catalog, so other projects can add
it and install in two steps:

```bash
# Add this repository as a plugin marketplace
/plugin marketplace add cairn-ai-tooling/agent-collab-tooling

# Install the plugin (and its skills)
/plugin install agent-collab-tooling@cairn-ai-agent-tooling
```

To try it locally from a clone:

```bash
/plugin marketplace add /path/to/this/repo
/plugin install agent-collab-tooling@cairn-ai-agent-tooling
```

Once installed, the skills are available to the agent automatically (and via `/agent-handoff`,
`/shared-task-tracking`, `/code-review-exchange`).

## Repository structure

```text
.
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest
│   └── marketplace.json     # Marketplace catalog (lists this plugin, source ".")
├── skills/                  # One directory per skill (SKILL.md + supporting files)
├── docs/decisions/          # Architecture Decision Records (ADRs)
├── test/manifests.test.mjs  # node:test invariant checks for the manifests + skills
├── .githooks/pre-commit     # Local lint + test gate
├── .github/workflows/ci.yml # CI: lint + test
├── CHANGELOG.md             # Keep a Changelog / SemVer
├── CLAUDE.md                # Guidance for agents working *in this repo*
├── package.json             # Dev tooling (markdownlint, test scripts)
├── LICENSE
└── README.md
```

## Development

This repo is mostly Markdown, so the tooling is lightweight. Run once to install the
linter and enable the pre-commit hook:

```bash
npm install        # installs markdownlint-cli2; the "prepare" script enables .githooks
```

Then:

```bash
npm run lint       # markdownlint over all Markdown
npm run lint:fix   # auto-fix what markdownlint can
npm test           # node:test — validates manifests + skill frontmatter
npm run check      # lint + test (what CI runs)
```

The tests enforce that `plugin.json` and `marketplace.json` stay version-synced and that
every skill has valid frontmatter. There is no type checking — there is no typed source;
the manifest tests serve the equivalent guardrail role. Rationale is recorded in
[`docs/decisions/0001-adopt-linting-tests-and-records.md`](docs/decisions/0001-adopt-linting-tests-and-records.md).

## Adding a new skill

1. Create `skills/<your-skill-name>/SKILL.md` (kebab-case directory name matching `name`).
2. Add YAML frontmatter with at least `name` and `description`; a precise `description`
   (and optional `when_to_use`) is what lets agents auto-invoke the skill at the right time.
3. Write concrete, actionable guidance — not a placeholder. State the rule, show the
   format, and give quality checks.
4. Add a row to the **Skills in this plugin** table above.
5. Add a `CHANGELOG.md` entry under `[Unreleased]` (use the `changelog` skill).
6. On release, bump the `version` in both
   [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) and the matching entry in
   [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) (kept in sync by
   the tests).
7. Run `npm run check` before committing.

## License

[MIT](LICENSE) © Steven Merriel / Cairn AI
