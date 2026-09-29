import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { runInNewContext } from "node:vm";
import ts from "typescript";

const source = readFileSync(path.resolve("src/app/submissions/new/form-draft.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const formDraft = {};
runInNewContext(compiled, { exports: formDraft });

test("submission draft restores text, selects, and checked consent after an action reset", () => {
  const controls = [
    { name: "device", value: "usb:1234:5678", type: "text" },
    { name: "os", value: "windows", type: "select-one" },
    { name: "consent", value: "yes", type: "checkbox", checked: true },
    { name: "consent", value: "no", type: "checkbox", checked: false },
  ];
  const form = { elements: controls };
  const draft = formDraft.captureSubmissionDraft(form);

  controls.forEach((control) => {
    if ("checked" in control) control.checked = false;
    else control.value = "";
  });
  formDraft.restoreSubmissionDraft(form, draft);

  assert.equal(controls[0].value, "usb:1234:5678");
  assert.equal(controls[1].value, "windows");
  assert.equal(controls[2].checked, true);
  assert.equal(controls[3].checked, false);
});

test("submission draft retains repeated named values in order", () => {
  const controls = [
    { name: "tag", value: "one", type: "text" },
    { name: "tag", value: "two", type: "text" },
  ];
  const form = { elements: controls };
  const draft = formDraft.captureSubmissionDraft(form);
  controls.forEach((control) => { control.value = ""; });
  formDraft.restoreSubmissionDraft(form, draft);

  assert.deepEqual(controls.map((control) => control.value), ["one", "two"]);
});
