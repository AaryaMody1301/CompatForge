import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import test from "node:test";

test("Next lint root discovery preserves directory-only glob semantics", () => {
  const require = createRequire(import.meta.url);
  const pluginEntry = require.resolve("@next/eslint-plugin-next");
  const { getRootDirs } = require(path.join(path.dirname(pluginEntry), "utils/get-root-dirs.js"));
  const workspace = mkdtempSync(path.join(tmpdir(), "compatforge-lint-"));
  try {
    mkdirSync(path.join(workspace, "apps/web"), { recursive: true });
    mkdirSync(path.join(workspace, "apps/docs"));
    writeFileSync(path.join(workspace, "apps/file.txt"), "not a directory");
    const roots = getRootDirs({
      cwd: workspace,
      settings: { next: { rootDir: [path.join(workspace, "apps/*"), "missing-root"] } },
    }).map((root) => path.resolve(root)).sort();
    assert.deepEqual(roots, [path.join(workspace, "apps/docs"), path.join(workspace, "apps/web")]);
    assert.deepEqual(getRootDirs({ cwd: workspace, settings: {} }), [workspace]);
  } finally {
    rmSync(workspace, { recursive: true, force: true });
  }
});
