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
|-------|--------------|
| [`agent-handoff`](skills/agent-handoff/SKILL.md) | Finishing work that another agent or a future session will continue — produces a structured handoff (goal, decisions, state, remaining work, blockers). |
| [`shared-task-tracking`](skills/shared-task-tracking/SKILL.md) | Multiple agents work toward a shared goal — defines a single `TASKS.md` source of truth and a claim/update/complete protocol that prevents double-work. |
| [`code-review-exchange`](skills/code-review-exchange/SKILL.md) | One agent asks another to review code — standardizes the review request and the severity-tagged review response. |

## Installing in another project

This repo is both a plugin **and** its own marketplace catalog, so other projects can add
it and install in two steps:

```bash
# Add this repository as a plugin marketplace
/plugin marketplace add cairn-ai/agent-collab-tooling

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

```
.
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest
│   └── marketplace.json     # Marketplace catalog (lists this plugin, source ".")
├── skills/
│   ├── agent-handoff/SKILL.md
│   ├── shared-task-tracking/SKILL.md
│   └── code-review-exchange/SKILL.md
├── CLAUDE.md                # Guidance for agents working *in this repo*
├── LICENSE
└── README.md
```

## Adding a new skill

1. Create `skills/<your-skill-name>/SKILL.md` (kebab-case directory name).
2. Add YAML frontmatter with at least `name` and `description`; a precise `description`
   (and optional `when_to_use`) is what lets agents auto-invoke the skill at the right time.
3. Write concrete, actionable guidance — not a placeholder. State the rule, show the
   format, and give quality checks.
4. Add a row to the **Skills in this plugin** table above.
5. Bump the `version` in [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) and the
   matching entry in [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json).

## License

[MIT](LICENSE) © Steven Merriel / Cairn AI
