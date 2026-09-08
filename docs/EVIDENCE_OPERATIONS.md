# Evidence coverage and stale-review operations

Phase 7D turns the read-only Phase 7A freshness/source-health artifacts and Phase 7B vendor semantic-change artifacts into a deterministic review dashboard and prioritized work queue.

It does not mutate canonical evidence, open evidence-changing pull requests, publish community submissions, or write to Supabase.

## Coverage model

The operations report groups reviewed evidence by canonical `device_id` and measures platform coverage at the operating-system-family/architecture level.

For observations, the platform cell comes from the exact reviewed host configuration, for example `windows/arm64`.

For vendor support statements, the platform cell comes from the declared support scope. A support scope with architecture `any` expands only to the two canonical observation architectures currently supported by CompatForge: `x86_64` and `arm64`.

Each device reports:

- observation and support-statement counts;
- unique source count;
- fresh, aging and stale evidence counts from the Phase 7A report;
- observed platform cells;
- vendor-supported platform cells;
- corroborated cells present in both sets;
- vendor-only cells where a reviewed reproduction is still missing;
- observed-only cells not currently covered by a vendor support statement;
- observed outcome counts;
- reviewed connection-path kinds.

This is deliberately a coarse coverage matrix. It does not claim that two records with the same OS family and architecture have identical OS versions, host models, drivers, software, topology or behavior.

## Priority queue

`compatforge_pipeline.evidence_operations` emits deterministic work items sorted by descending integer score.

Priority bands are:

- `P0`: score 450 or greater;
- `P1`: score 300-449;
- `P2`: score 180-299;
- `P3`: score below 180.

The score is review triage, not compatibility confidence.

Current task types are:

- `vendor_semantic_change`: a permitted vendor adapter changed reviewed semantic facts (`500`) or lacks a reviewed baseline (`350`);
- `source_health`: a referenced source is currently unreachable (`450`);
- `stale_evidence`: base `300` plus bounded age beyond 365 days;
- `aging_evidence`: base `180` plus bounded age beyond 180 days;
- `reproduction_gap`: vendor support exists for an OS-family/architecture cell with no reviewed observation (`140`).

A stale or aging record receives an additional `100` points if one of its sources is unreachable and an additional `120` points if one of its permitted vendor sources has a semantic change. Combined evidence-item scores are capped at `599`.

The queue is deterministic for identical input artifacts. Its SHA-256 is recorded in the JSON output.

## Weekly review artifact

`.github/workflows/refresh-evidence.yml` remains read-only with `contents: read`.

The scheduled/manual workflow now generates:

- `freshness.json` and its Markdown summary;
- `source-checks.json`;
- `vendor-snapshot.json`;
- `vendor-changes.json` and its Markdown summary;
- `operations.json`;
- `operations.md`.

The combined Markdown operations dashboard is also appended to the GitHub Actions job summary.

The workflow deliberately runs at minute 43 rather than at the start of the hour. GitHub notes that scheduled workflows can be delayed during high-load periods, especially around the start of an hour.

## FTDI D2XX adapter

Phase 7D adds the official FTDI D2XX driver page to the exact-host HTTPS allowlist.

The reviewed semantic baseline records only small compatibility-relevant facts:

- Windows Desktop release date, x64 version and ARM64 version;
- Windows Universal ARM64 version;
- the Windows ARM64 installer limitation;
- Linux release date, x64 version and ARMv8 version;
- macOS release date, x64 version and ARM version.

The adapter does not mirror the vendor page. Live HTML is bounded to 2 MiB, parsed into the reviewed semantic object, hashed, compared with `data/sources/vendor-adapters/ftdi_d2xx.json`, and discarded with the workflow runner.

A semantic delta is a review signal only. It never rewrites `data/evidence`.

## Local use

After generating the Phase 7A and Phase 7B inputs, build the operations report with:

```bash
python -m compatforge_pipeline.evidence_operations build \
  --observations data/evidence/observations \
  --support data/evidence/vendor \
  --freshness build/evidence-review/freshness.json \
  --source-checks build/evidence-review/source-checks.json \
  --vendor-changes build/evidence-review/vendor-changes.json \
  --output build/evidence-review/operations.json \
  --summary build/evidence-review/operations.md
```

Reviewers still decide whether evidence needs a source refresh, new reproduction, semantic update, or no change.
