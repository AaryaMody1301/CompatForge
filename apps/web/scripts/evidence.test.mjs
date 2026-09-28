import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { runInNewContext } from "node:vm";
import ts from "typescript";

const source = readFileSync(path.resolve("src/lib/evidence.ts"), "utf8");
const observation = {
  observation_id: "obs_fixture", device_id: "usb:1234:5678",
  host: { manufacturer: "Acme", model: "Host A", architecture: "arm64",
    operating_system: { family: "windows", version: "11", build: "26100" } },
  connection_path: [{ kind: "usb_hub" }, { kind: "cable" }],
  driver: { name: "VCP", version: "2.1" },
  software: { name: "avrdude", version: "8.1" },
  firmware_version: "1.0", outcome: "works", conditions: [],
  evidence: { source_type: "independent_reproduction", source_url: "https://example.com",
    source_title: "Test" }, observed_at: "2026-01-01T00:00:00Z",
  recorded_at: "2026-01-01T00:00:00Z",
};
const support = {
  statement_id: "sup_fixture", device_id: observation.device_id,
  scope: { architecture: "arm64", operating_system: {
    family: "windows", version_mode: "minimum", minimum_version: "10.0",
  }, connection: { kind: "any_usb", minimum_usb_generation: "2.0" } },
  support_status: "supported", evidence: { source_type: "vendor_documentation",
    sources: [{ source_url: "https://example.com", source_title: "Test" }], source_note: "Test" },
  reviewed_at: "2026-01-01T00:00:00Z", recorded_at: "2026-01-01T00:00:00Z",
};

function resolver(observations = [observation], statements = [support]) {
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const exported = {};
  runInNewContext(output, {
    exports: exported,
    require(id) {
      assert.equal(id, "./evidence.generated");
      return {
        canonicalObservationDocuments: observations,
        canonicalSupportStatementDocuments: statements,
      };
    },
    Intl, Date, Set,
  });
  return exported;
}

function query(overrides = {}) {
  return {
    deviceId: observation.device_id, architecture: "arm64", osFamily: "windows",
    osVersion: "11", connectionKind: "usb_hub",
    connectionPath: ["usb_hub", "cable"],
    hostManufacturer: "Acme", hostModel: "Host A", ...overrides,
  };
}

test("web resolver matches a two-hop path and reports unchecked dimensions", () => {
  const result = resolver().resolveCompatibility(query());
  assert.equal(result.claimState, "works");
  assert.equal(result.specificity, "exact");
  assert.ok(result.uncheckedDimensions.includes("driver version"));
});

for (const [dimension, altered] of [
  ["osBuild", "99999"], ["driverName", "Other driver"], ["driverVersion", "99"],
  ["softwareName", "Other program"], ["softwareVersion", "99"],
  ["firmwareVersion", "99"],
]) {
  test(`web resolver does not discard supplied ${dimension}`, () => {
    const result = resolver().resolveCompatibility(query({ [dimension]: altered }));
    assert.equal(result.claimState, "unknown");
  });
}

test("web vendor support enforces a known minimum USB generation", () => {
  assert.equal(resolver().resolveCompatibility(query({ osVersion: "10", usbGeneration: "1.1" })).supportState, "unknown");
  assert.equal(resolver().resolveCompatibility(query({ osVersion: "10", usbGeneration: "2.0" })).supportState, "supported");
});

test("web resolver rejects invalid OS versions even outside the form", () => {
  const result = resolver().resolveCompatibility(query({ osVersion: "garbage" }));
  assert.equal(result.claimState, "unknown");
  assert.equal(result.supportState, "unknown");
  assert.equal(result.invalidFields[0], "OS version");
});

test("evidence age labels old records without deleting them", () => {
  const age = resolver().evidenceAge("2025-01-01T00:00:00Z", new Date("2026-09-28T00:00:00Z"));
  assert.equal(age.status, "stale");
  assert.ok(age.days > 365);
});
