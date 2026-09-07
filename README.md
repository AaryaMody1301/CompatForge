# CompatForge

Evidence-first hardware compatibility intelligence.

CompatForge is being built to answer a narrow but difficult question:

> Will this peripheral work with this host, operating system, architecture, driver, firmware, and connection path - and what evidence supports that answer?

The project treats compatibility as a configuration-level evidence problem rather than a binary device-to-laptop lookup. Missing evidence stays `UNKNOWN`; conflicting evidence stays visible; source observations are never rewritten into stronger claims than they support.

## Current build status

**Phase 1 - foundation and evidence contracts:** complete.

**Phase 2 - hardware identity data platform:** active. The implementation now includes reviewed USB identity ingestion, content-addressed raw snapshots, source manifests, Bronze Parquet/DuckDB tables, dbt staging/intermediate/mart models, deterministic public snapshot export, and scheduled refresh candidates.

No real-world compatibility result is published by Phase 2. Identity registries establish what a device is; they do not establish whether it works.

## Initial scope

The first public compatibility release will focus on developer and engineering USB peripherals:

- USB serial adapters;
- development boards;
- debuggers/programmers;
- logic analyzers.

Initial operating-system scope is Windows 11, macOS, and Ubuntu on `x86_64` and `arm64`. Direct USB and hub-mediated connections will be modeled explicitly when compatibility evidence begins in Phase 3.

## Repository layout

```text
apps/web/                     Next.js product shell
pipeline/compatforge_pipeline Python identity/evidence tooling
dbt/compatforge/               DuckDB/dbt identity transformations
data/sources/                  reviewed upstream-source contracts
data/fixtures/                 synthetic evidence fixtures
schemas/                       public JSON Schema contracts
tests/                         contract and pipeline regression tests
docs/                          architecture, data, evidence, privacy, roadmap
.github/workflows/             CI and reviewed refresh workflows
```

## Validate contracts

Python 3.13+:

```bash
python -m pip install -e ".[dev]"
python -m compatforge_pipeline.validate data/fixtures
pytest -q
ruff check pipeline tests
```

## Build the identity platform locally

```bash
python -m pip install -e ".[dev,data]"

python -m compatforge_pipeline.identity_pipeline bronze \
  --workspace build/local \
  --input tests/fixtures/usb.ids \
  --retrieved-at 2026-01-01T00:00:00Z \
  --source-url synthetic://tests/fixtures/usb.ids

export COMPATFORGE_DUCKDB_PATH="$PWD/build/local/compatforge.duckdb"
dbt build --project-dir dbt/compatforge --profiles-dir dbt/compatforge
python -m compatforge_pipeline.identity_pipeline snapshot --workspace build/local
```

To build a live refresh candidate, omit `--input`, `--retrieved-at`, and `--source-url`. The downloader uses the reviewed upstream URL and an identifying User-Agent.

## Run the web shell

From `apps/web`:

```bash
npm ci
npm run dev
```

## Evidence rule

A compatibility observation must identify, at minimum:

- what device was involved;
- the host and CPU architecture;
- the operating system and version;
- the connection path;
- the observed outcome;
- the evidence source and source type;
- when the result was observed and recorded.

See [`docs/EVIDENCE_MODEL.md`](docs/EVIDENCE_MODEL.md).

## Project principles

1. Unknown is a valid result.
2. Evidence and derived claims are separate records.
3. Hardware identity and compatibility outcomes are separate data domains.
4. Compatibility specificity must never be silently broadened.
5. Conflicting evidence is preserved, not averaged away.
6. Raw source provenance and licensing are release requirements.
7. Diagnostic collection must be inspectable and privacy-minimized.

## License

Project source code is MIT licensed. Third-party source data keeps its upstream license and attribution requirements; see `THIRD_PARTY_NOTICES.md` and per-snapshot manifests.
