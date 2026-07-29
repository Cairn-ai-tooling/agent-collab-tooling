# 0004 — Test the skills' bundled Python scripts with uv + pytest

**Status:** Accepted

## Context

Skills may bundle Python helper scripts under `skills/<name>/assets/scripts/` (the
`product-item` skill ships a scaffolder and an integrity-gate validator, and more are expected
as skills grow). Until now the repo's only automated tests were `node:test` manifest checks
(`test/manifests.test.mjs`); the Python scripts had **no test coverage in this repo** — the
drift-guard tests their docstrings referenced lived in the projects they were extracted from.

That left the scripts' behaviour — gap-safe numbering, YAML-safe titles, the `--with-plan`
cross-wiring, and the scaffolder↔validator parity — unverified here, exactly where the merged,
decoupled versions now live. We need a Python test runner, and it has to fit a repo whose
primary toolchain is Node.

## Decision

- Adopt **pytest**, run through **`uv`** (`uv run pytest`), configured by a root
  `pyproject.toml` (a non-published virtual project; dev deps `pytest` + `pyyaml`).
- Tests live under `tests/` (pytest) — separate from the Node tests in `test/`. A
  `tests/conftest.py` puts each skill's `scripts/` dir on `sys.path` so the bundled scripts
  import by module name despite not being an installed package.
- Wire it into the existing gates: `npm run test:py` (and `npm test` = node + Python), so the
  pre-commit hook and CI run both. CI installs `uv` via `astral-sh/setup-uv`; the pre-commit
  hook fails with a clear message if `uv` is absent.
- `.venv/` / caches are gitignored; `uv.lock` is committed for reproducible runs.

## Why

- **`uv` matches an existing convention.** The skills already invoke their scripts with
  `uv run python …` in `SKILL.md`/README, and `uv` was already present in the dev environment.
  Reusing it keeps one Python entry point instead of introducing a second (pip/venv) workflow.
- **Isolated, reproducible, fast.** `uv run` creates and manages a `.venv` on demand, so
  contributors don't install into system Python and CI needs no bespoke setup beyond the uv
  action. The scripts already depend on `pyyaml` at runtime, so a managed env is needed anyway.
- **pytest over stdlib `unittest`.** With more Python scripts expected, pytest's fixtures
  (`tmp_path`, `monkeypatch`) and terse assertions keep per-script test cost low; the ergonomic
  gap over `unittest` compounds as coverage grows.
- **Consistent with ADR 0001's guardrail role.** There is no typed source here; tests are the
  equivalent guardrail, and the Python scripts deserve the same protection the manifests get.

## Consequences

- Contributors (and CI) now need **`uv`** in addition to Node. This is a new prerequisite,
  documented in the README/CLAUDE.md dev sections and enforced by the pre-commit hook.
- `npm test` is now node + Python; a machine without `uv` cannot run the full gate (by design —
  the hook says so explicitly).
- New skill Python scripts are expected to ship with tests under `tests/`; the
  `tests/conftest.py` shim is the pattern for importing skill-asset scripts.
- The scaffolder↔validator drift guards (status set, type map) now run in CI, so divergence
  between the two `product-item` scripts fails the build instead of silently rotting.
