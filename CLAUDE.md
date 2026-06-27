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
  another project run `/plugin marketplace add cairn-ai/agent-collab-tooling` and then
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
in this plugin" table, and bump `version` in both manifests.

## Validating changes

There is no test suite. Before committing, verify mechanically:

```bash
python3 -m json.tool .claude-plugin/plugin.json
python3 -m json.tool .claude-plugin/marketplace.json
```

To smoke-test discovery locally from a clone:

```bash
/plugin marketplace add /path/to/this/repo
/plugin install agent-collab-tooling@cairn-ai-agent-tooling
```

## Notes

- `.remember/` is local session tooling and is gitignored — never commit it.
- This is a plugin *source* repo, not a project that gets deployed; ignore the Vercel/AWS
  session tooling unless explicitly asked.
