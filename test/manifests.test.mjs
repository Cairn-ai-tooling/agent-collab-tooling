import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const readJSON = (rel) => JSON.parse(readFileSync(join(repoRoot, rel), "utf8"));

const plugin = readJSON(".claude-plugin/plugin.json");
const marketplace = readJSON(".claude-plugin/marketplace.json");

test("plugin.json has required fields", () => {
  assert.ok(plugin.name, "plugin.name is required");
  assert.match(plugin.name, /^[a-z0-9]+(-[a-z0-9]+)*$/, "plugin.name must be kebab-case");
  assert.ok(plugin.version, "plugin.version is required");
  assert.match(plugin.version, /^\d+\.\d+\.\d+$/, "plugin.version must be semver");
});

test("marketplace.json has required shape", () => {
  assert.ok(marketplace.name, "marketplace.name is required");
  assert.ok(marketplace.owner?.name, "marketplace.owner.name is required");
  assert.ok(Array.isArray(marketplace.plugins) && marketplace.plugins.length > 0,
    "marketplace.plugins must be a non-empty array");
});

test("marketplace lists this plugin and stays version-synced", () => {
  const entry = marketplace.plugins.find((p) => p.name === plugin.name);
  assert.ok(entry, `marketplace must list a plugin named "${plugin.name}"`);
  // The two manifests are coupled; drift here is the bug this test exists to catch.
  assert.equal(entry.version, plugin.version,
    "marketplace plugin entry version must match plugin.json version");
});

test("plugin.skills path exists", () => {
  const skillsPath = (plugin.skills ?? "./skills/").replace(/^\.\//, "");
  assert.ok(existsSync(join(repoRoot, skillsPath)), `${skillsPath} must exist`);
});

// Parse just enough of the YAML frontmatter to assert the contract — no YAML dependency.
function frontmatter(md) {
  const m = md.match(/^---\n([\s\S]*?)\n---/);
  if (!m) return null;
  const fields = {};
  for (const line of m[1].split("\n")) {
    const kv = line.match(/^([A-Za-z0-9_-]+):\s*(.+)$/);
    if (kv) fields[kv[1]] = kv[2].trim();
  }
  return fields;
}

const skillsDir = join(repoRoot, "skills");
const skillDirs = readdirSync(skillsDir).filter((d) =>
  statSync(join(skillsDir, d)).isDirectory());

test("at least one skill is present", () => {
  assert.ok(skillDirs.length > 0, "skills/ must contain at least one skill");
});

for (const dir of skillDirs) {
  test(`skill "${dir}" has valid SKILL.md frontmatter`, () => {
    const skillPath = join(skillsDir, dir, "SKILL.md");
    assert.ok(existsSync(skillPath), `${dir}/SKILL.md must exist`);
    const fm = frontmatter(readFileSync(skillPath, "utf8"));
    assert.ok(fm, `${dir}/SKILL.md must start with YAML frontmatter`);
    assert.ok(fm.name, `${dir}/SKILL.md frontmatter must set name`);
    assert.ok(fm.description, `${dir}/SKILL.md frontmatter must set description`);
    assert.equal(fm.name, dir, `${dir}/SKILL.md name must match its directory`);
  });
}
