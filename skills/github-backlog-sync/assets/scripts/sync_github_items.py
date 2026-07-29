"""Mirror the local ``docs/product/`` backlog to GitHub Issues (and optionally a Project).

Why this script exists
======================

``/product-item`` tracks work as local Markdown artifacts. Once a project is big enough
(see the size metric in ``SKILL.md``) teams want that backlog visible on GitHub — Issues for
assignment/comments/PR cross-references, and optionally a Project board. Doing that by hand is
tedious and easy to get wrong (duplicate issues, drifted status). This script makes the sync
**deterministic and idempotent**:

- The local artifact stays the **source of truth**; each Issue is a mirror that links back.
- The Issue number is recorded into the artifact frontmatter (``github_issue:``), so a re-run
  **updates** the existing Issue instead of creating a duplicate.
- It is **plan-only by default**; mutating GitHub requires ``--apply``. The only local write is
  recording ``github_issue:`` / ``github_project_item:`` back into frontmatter.

Design: the sync engine (load → plan → apply → write-back) is backend-agnostic — it talks to an
``IssueBackend`` interface, so it is unit-testable against a fake backend with no network. The
concrete backend here drives the ``gh`` CLI. (The GitHub MCP server is the *other* backend from
the design, but MCP tools are invoked by the agent, not a subprocess — so when only MCP is
available the agent runs the same steps itself, per ``SKILL.md``'s MCP fallback.)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DIR = REPO_ROOT / "docs" / "product"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
ISSUE_BODY_TEMPLATE = TEMPLATES_DIR / "issue-body-template.md"

# Artifact type -> (directory, GitHub label). Kept parallel to product-item's TYPE_SPEC.
TYPES: dict[str, tuple[str, str]] = {
    "epic": ("epics", "epic"),
    "story": ("stories", "story"),
    "task": ("tasks", "task"),
    "plan": ("implementation-plans", "plan"),
}

# Statuses that mean the work is finished — the Issue is closed for these, open otherwise.
CLOSED_STATUSES = {"Done", "Archived"}

# The lifecycle values a Project single-select "Status" field mirrors (same names as the
# artifact status), kept in lock-step with product-item's VALID_STATUSES.
PROJECT_STATUSES = ("Proposed", "Ready", "In Progress", "In Review", "Done", "Archived")


# --------------------------------------------------------------------------------------------
# Frontmatter I/O
# --------------------------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a Markdown document into its YAML frontmatter mapping and body.

    Returns ``({}, text)`` for a file that doesn't open with a ``---`` fence or whose fence is
    not a YAML mapping — so a malformed file is skipped, not crashed on. Self-contained (stdlib
    + pyyaml), matching the product-item scripts.
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n---", 1)
    if len(parts) != 2:
        return {}, text
    try:
        meta = yaml.safe_load(parts[0][len("---"):])
    except yaml.YAMLError:
        return {}, text
    if not isinstance(meta, dict):
        return {}, text
    return meta, parts[1].lstrip("\n")


def set_frontmatter_field(path: Path, key: str, value: object) -> None:
    """Record ``key: value`` in a file's frontmatter, editing only that one line.

    Replaces the line in place if the key exists, otherwise inserts it just before the closing
    ``---`` fence. Deliberately a targeted text edit (not a YAML re-dump) so the rest of the
    artifact — field order, comments, spacing — is left exactly as the author wrote it.
    """
    text = path.read_text(encoding="utf-8")
    line = f"{key}: {value}"
    key_re = re.compile(rf"^{re.escape(key)}:.*$", re.MULTILINE)
    if key_re.search(text):
        path.write_text(key_re.sub(line, text, count=1), encoding="utf-8")
        return
    # Insert before the frontmatter's closing fence (the second ``---``).
    fence = re.compile(r"^---\s*$", re.MULTILINE)
    fences = list(fence.finditer(text))
    if len(fences) < 2:
        raise ValueError(f"{path}: no frontmatter block to add {key!r} to")
    at = fences[1].start()
    path.write_text(f"{text[:at]}{line}\n{text[at:]}", encoding="utf-8")


# --------------------------------------------------------------------------------------------
# Artifact model
# --------------------------------------------------------------------------------------------

@dataclass
class Artifact:
    path: Path
    type_key: str
    meta: dict[str, Any]
    body: str

    @property
    def id(self) -> str:
        return str(self.meta.get("id", ""))

    @property
    def title(self) -> str:
        return str(self.meta.get("title", ""))

    @property
    def status(self) -> str:
        return str(self.meta.get("status", "Proposed"))

    @property
    def github_issue(self) -> int | None:
        raw = self.meta.get("github_issue")
        return int(raw) if isinstance(raw, int) or (isinstance(raw, str) and raw.isdigit()) else None

    @property
    def is_open(self) -> bool:
        return self.status not in CLOSED_STATUSES


def load_artifacts(product_dir: Path) -> list[Artifact]:
    """Load every artifact under ``product_dir`` with well-formed frontmatter, sorted by id."""
    artifacts: list[Artifact] = []
    for type_key, (directory, _label) in TYPES.items():
        d = product_dir / directory
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.md")):
            meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            if meta:
                artifacts.append(Artifact(path=path, type_key=type_key, meta=meta, body=body))
    return artifacts


def open_epic_count(artifacts: list[Artifact]) -> int:
    return sum(1 for a in artifacts if a.type_key == "epic" and a.is_open)


def backlog_counts(artifacts: list[Artifact]) -> dict[str, int]:
    """Counts that drive the size metric / recommendation."""
    return {
        "total": len(artifacts),
        "open": sum(1 for a in artifacts if a.is_open),
        "open_epics": open_epic_count(artifacts),
    }


# --------------------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------------------

def issue_title(artifact: Artifact) -> str:
    """``<ID> <title>`` so issues stay greppable by artifact id."""
    return f"{artifact.id} {artifact.title}".strip()


def render_issue_body(artifact: Artifact, template: str) -> str:
    """Fill the issue-body template from the artifact. The whole body is managed by the sync and
    regenerated on each update; human discussion belongs in Issue *comments*, which are never
    touched."""
    parent = ""
    for field in ("epic", "story", "covers"):
        value = artifact.meta.get(field)
        if isinstance(value, str) and re.match(r"^(EPIC|STORY|TASK|PLAN)-\d{3}$", value):
            parent = f"{field}: `{value}`"
            break
    return (
        template
        .replace("{id}", artifact.id)
        .replace("{type}", artifact.type_key)
        .replace("{status}", artifact.status)
        .replace("{artifact_path}", str(artifact.path))
        .replace("{parent}", parent or "_none_")
        .replace("{body}", artifact.body.strip())
    )


# --------------------------------------------------------------------------------------------
# Sync plan
# --------------------------------------------------------------------------------------------

@dataclass
class PlanItem:
    artifact: Artifact
    action: str  # "create" or "update"
    title: str
    label: str
    is_open: bool
    project_status: str

    def describe(self) -> str:
        state = "open" if self.is_open else "closed"
        existing = f"#{self.artifact.github_issue}" if self.artifact.github_issue else "(new)"
        return f"{self.action:6} {existing:6} [{self.label:5}] {state:6} {self.title}"


def build_plan(artifacts: list[Artifact]) -> list[PlanItem]:
    """Decide create-vs-update per artifact and compute its target Issue shape. Pure — no I/O —
    so it is trivially testable and produces the same result the dry-run prints and ``--apply``
    executes."""
    plan: list[PlanItem] = []
    for artifact in artifacts:
        plan.append(
            PlanItem(
                artifact=artifact,
                action="update" if artifact.github_issue else "create",
                title=issue_title(artifact),
                label=TYPES[artifact.type_key][1],
                is_open=artifact.is_open,
                project_status=artifact.status if artifact.status in PROJECT_STATUSES else "Proposed",
            )
        )
    return plan


# --------------------------------------------------------------------------------------------
# Backend interface + concrete gh CLI adapter
# --------------------------------------------------------------------------------------------

class IssueBackend(ABC):
    """The seam between the sync engine and GitHub. A fake implementation makes the whole engine
    testable without a network; ``GhCliBackend`` is the real one."""

    @abstractmethod
    def create_issue(self, *, title: str, body: str, label: str) -> int:
        ...

    @abstractmethod
    def update_issue(self, number: int, *, title: str, body: str, label: str) -> None:
        ...

    @abstractmethod
    def set_issue_state(self, number: int, *, is_open: bool) -> None:
        ...

    @abstractmethod
    def add_to_project(self, number: int) -> str:
        ...

    @abstractmethod
    def set_project_status(self, item_id: str, *, status: str) -> None:
        ...


@dataclass
class GhCliBackend(IssueBackend):
    """Drives the ``gh`` CLI. Issue create/update/state are well-defined ``gh issue`` calls;
    Project support uses ``gh project`` (Projects v2 / GraphQL) and caches the board's field and
    option ids. Project wiring should be smoke-tested against a real board before it is relied on.
    """

    repo: str
    project: int | None = None
    project_owner: str | None = None
    _project_meta: dict[str, Any] | None = None

    def _gh(self, *args: str, stdin: str | None = None) -> str:
        result = subprocess.run(
            ["gh", *args],
            input=stdin,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def create_issue(self, *, title: str, body: str, label: str) -> int:
        url = self._gh(
            "issue", "create", "--repo", self.repo,
            "--title", title, "--label", label, "--body-file", "-",
            stdin=body,
        )
        match = re.search(r"/issues/(\d+)\s*$", url)
        if not match:
            raise RuntimeError(f"could not parse issue number from: {url!r}")
        return int(match.group(1))

    def update_issue(self, number: int, *, title: str, body: str, label: str) -> None:
        self._gh(
            "issue", "edit", str(number), "--repo", self.repo,
            "--title", title, "--add-label", label, "--body-file", "-",
            stdin=body,
        )

    def set_issue_state(self, number: int, *, is_open: bool) -> None:
        verb = "reopen" if is_open else "close"
        self._gh("issue", verb, str(number), "--repo", self.repo)

    # --- Projects v2 (owner defaults to the repo owner) ---

    def _owner(self) -> str:
        return self.project_owner or self.repo.split("/", 1)[0]

    def _meta(self) -> dict[str, Any]:
        if self._project_meta is None:
            view = json.loads(
                self._gh("project", "view", str(self.project), "--owner", self._owner(), "--format", "json")
            )
            fields = json.loads(
                self._gh("project", "field-list", str(self.project), "--owner", self._owner(), "--format", "json")
            )
            status = next(
                (f for f in fields.get("fields", []) if f.get("name") == "Status"), None
            )
            self._project_meta = {"project_id": view["id"], "status_field": status}
        return self._project_meta

    def add_to_project(self, number: int) -> str:
        url = f"https://github.com/{self.repo}/issues/{number}"
        added = json.loads(
            self._gh("project", "item-add", str(self.project), "--owner", self._owner(),
                     "--url", url, "--format", "json")
        )
        return added["id"]

    def set_project_status(self, item_id: str, *, status: str) -> None:
        meta = self._meta()
        field = meta["status_field"]
        if not field:
            raise RuntimeError("project has no single-select 'Status' field to set")
        option = next((o for o in field.get("options", []) if o.get("name") == status), None)
        if not option:
            raise RuntimeError(f"project 'Status' field has no option named {status!r}")
        self._gh(
            "project", "item-edit", "--id", item_id, "--project-id", meta["project_id"],
            "--field-id", field["id"], "--single-select-option-id", option["id"],
        )


# --------------------------------------------------------------------------------------------
# Apply
# --------------------------------------------------------------------------------------------

@dataclass
class SyncResult:
    artifact_id: str
    action: str
    number: int


def apply_plan(
    plan: list[PlanItem],
    backend: IssueBackend,
    *,
    body_template: str,
    use_project: bool,
) -> list[SyncResult]:
    """Execute the plan against ``backend`` and record ids back into each artifact's frontmatter.

    This is where idempotency is realised: a freshly-created issue's number is written to
    ``github_issue:`` immediately, so a subsequent run sees it and updates instead of recreating.
    """
    results: list[SyncResult] = []
    for item in plan:
        artifact = item.artifact
        body = render_issue_body(artifact, body_template)

        if item.action == "create":
            number = backend.create_issue(title=item.title, body=body, label=item.label)
            set_frontmatter_field(artifact.path, "github_issue", number)
        else:
            number = artifact.github_issue  # guaranteed by build_plan
            backend.update_issue(number, title=item.title, body=body, label=item.label)

        backend.set_issue_state(number, is_open=item.is_open)

        if use_project:
            existing_item = artifact.meta.get("github_project_item")
            item_id = existing_item if isinstance(existing_item, str) else backend.add_to_project(number)
            if not existing_item:
                set_frontmatter_field(artifact.path, "github_project_item", item_id)
            backend.set_project_status(item_id, status=item.project_status)

        results.append(SyncResult(artifact_id=artifact.id, action=item.action, number=number))
    return results


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------

def _print_plan(plan: list[PlanItem], counts: dict[str, int], *, use_project: bool) -> None:
    print(f"Backlog: {counts['total']} artifacts, {counts['open']} open, "
          f"{counts['open_epics']} open epic(s).")
    creates = sum(1 for p in plan if p.action == "create")
    updates = len(plan) - creates
    print(f"Plan: {creates} to create, {updates} to update"
          + (" (+ project board)" if use_project else "") + ".\n")
    for item in plan:
        print("  " + item.describe())
    print("\n(dry-run — nothing written. Re-run with --apply to sync.)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mirror docs/product artifacts to GitHub Issues.")
    parser.add_argument("product_dir", nargs="?", default=str(PRODUCT_DIR),
                        help="path to the product backlog (default: docs/product)")
    parser.add_argument("--repo", required=True, help="target GitHub repo, owner/name")
    parser.add_argument("--project", type=int, help="GitHub Project number to add issues to")
    parser.add_argument("--project-owner", help="Project owner (default: the repo owner)")
    parser.add_argument("--apply", action="store_true",
                        help="actually write to GitHub (default: plan only)")
    args = parser.parse_args(argv)

    product_dir = Path(args.product_dir)
    if not product_dir.is_dir():
        print(f"error: not a directory: {product_dir}", file=sys.stderr)
        return 2

    artifacts = load_artifacts(product_dir)
    if not artifacts:
        print(f"No artifacts found under {product_dir} — nothing to sync.")
        return 0

    plan = build_plan(artifacts)
    counts = backlog_counts(artifacts)
    use_project = args.project is not None

    if not args.apply:
        _print_plan(plan, counts, use_project=use_project)
        return 0

    body_template = ISSUE_BODY_TEMPLATE.read_text(encoding="utf-8")
    backend = GhCliBackend(repo=args.repo, project=args.project, project_owner=args.project_owner)
    results = apply_plan(plan, backend, body_template=body_template, use_project=use_project)

    created = [r for r in results if r.action == "create"]
    updated = [r for r in results if r.action == "update"]
    print(f"Synced {len(results)} artifact(s): {len(created)} created, {len(updated)} updated.")
    for r in results:
        print(f"  {r.artifact_id} -> #{r.number} ({r.action})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
