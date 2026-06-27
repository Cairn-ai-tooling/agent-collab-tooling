# 0002 — Keep markdownlint-cli2 and accept residual dev-only advisories

**Status:** Accepted

## Context

`npm audit` reports moderate-severity advisories in `js-yaml` and `markdown-it`, which
reach us transitively through `markdownlint-cli2` (our only dev dependency, used to lint
Markdown). We upgraded `markdownlint-cli2` to the latest `0.22.1`, which cleared two of the
original four advisories (a js-yaml prototype-pollution and a markdown-it ReDoS). Two
remain:

- `GHSA-h67p-54hq-rp68` — js-yaml quadratic-complexity DoS in YAML merge keys.
- `GHSA-6v5v-wf23-fmfq` — markdown-it quadratic-complexity DoS in the smartquotes rule.

Fixed versions exist (`js-yaml` 4.2.0+, `markdown-it` 14.2.0), but `markdownlint-cli2`
hard-pins `js-yaml@4.1.1`, so reaching them requires either npm `overrides` or `npm audit
fix --force` — and `--force` actually *downgrades* `markdownlint-cli2` to 0.12.1, the
opposite of staying current.

## Decision

- Stay on `markdownlint-cli2` at the latest version (`^0.22.1`).
- Do **not** add `overrides` and do **not** run `npm audit fix --force`.
- Accept the two residual advisories and record why here.
- Re-evaluate when `markdownlint-cli2` relaxes its `js-yaml` pin or ships the fixed
  transitive versions.

## Why

- Both advisories are **dev-only**: `markdownlint-cli2` is a lint tool that is never
  shipped to consumers of the plugin (consumers install only the Markdown skills).
- Both are **quadratic-complexity DoS** bugs that require feeding adversarial input to the
  parser. The linter only ever processes this repo's own, trusted Markdown — there is no
  untrusted-input path, so the bugs are not exploitable in our usage.
- Why not `overrides`: they work, but add ongoing maintenance (re-verify on every
  `markdownlint-cli2` bump) for a tool we are barely coupled to — overhead out of
  proportion to a non-exploitable dev-only risk.
- Why not switch to `remark-lint` (which has a natively clean `npm audit`): it roughly
  triples the dependency count (~192 vs ~81 packages) and requires rewriting the lint
  config and rule set, again disproportionate to the benefit here.
- Our CI and pre-commit run `lint` + `test`, not `npm audit`, so these advisories do not
  gate development.

## Consequences

- `npm install` / `npm audit` will continue to show two moderate advisories until upstream
  `markdownlint-cli2` updates its pins; this is expected, not a regression.
- The `markdownlint-cli2` 0.22.1 upgrade bundles `markdownlint` 0.40.0, which adds new
  default rules (e.g. `MD060` table-column-style); existing Markdown was updated to comply.
- If this repo ever lints untrusted/third-party Markdown, revisit this decision — the
  threat model would change.
