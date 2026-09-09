import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import ts from "typescript";

async function loadNavigationModule() {
  const sourcePath = path.resolve("src/lib/navigation.ts");
  const source = await readFile(sourcePath, "utf8");
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;

  const tempDirectory = await mkdtemp(path.join(os.tmpdir(), "compatforge-navigation-"));
  const outputPath = path.join(tempDirectory, "navigation.mjs");
  await writeFile(outputPath, output, "utf8");

  try {
    return await import(pathToFileURL(outputPath).href);
  } finally {
    await rm(tempDirectory, { recursive: true, force: true });
  }
}

const { safeInternalPath } = await loadNavigationModule();

test("safeInternalPath preserves same-origin paths", () => {
  assert.equal(safeInternalPath("/submissions/new?draft=1#form"), "/submissions/new?draft=1#form");
});

test("safeInternalPath rejects absolute and protocol-relative URLs", () => {
  assert.equal(safeInternalPath("https://evil.example/"), "/submissions");
  assert.equal(safeInternalPath("//evil.example/"), "/submissions");
});

test("safeInternalPath rejects backslash URL parser bypasses", () => {
  assert.equal(safeInternalPath("/\\evil.example/"), "/submissions");

  const decoded = new URL("https://compatforge.invalid/?next=/%5Cevil.example/").searchParams.get(
    "next",
  );
  assert.equal(decoded, "/\\evil.example/");
  assert.equal(safeInternalPath(decoded), "/submissions");
});

test("safeInternalPath falls back for missing values", () => {
  assert.equal(safeInternalPath(null), "/submissions");
  assert.equal(safeInternalPath("submissions"), "/submissions");
});
