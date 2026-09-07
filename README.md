# CompatForge

Evidence-first hardware compatibility intelligence.

CompatForge is being built to answer a narrow but difficult question:

> Will this peripheral work with this host, operating system, architecture, driver, firmware, and connection path - and what evidence supports that answer?

The project treats compatibility as a configuration-level evidence problem rather than a binary device-to-laptop lookup. Missing evidence stays `UNKNOWN`; conflicting evidence stays visible; source observations are never rewritten into stronger claims than they support.

## Current build status

**Phase 1 - foundation and evidence contracts:** complete.

**Phase 2 - hardware identity data platform:** complete. The repository has reviewed USB identity ingestion, content-addressed raw snapshots, source manifests, Bronze Parquet/DuckDB tables, dbt staging/intermediate/mart models, deterministic public snapshot export, and scheduled refresh candidates.

**Phase 3A - evidence semantics and deterministic resolver:** complete.

**Phase 3B - normalized evidence data platform:** in review. The branch adds DuckDB evidence ingestion, normalized dbt evidence dimensions/facts, deterministic freshness and coverage models, reviewed real-world evidence, and reproducible JSONL/Parquet evidence snapshots.

## Initial scope

The first public compatibility release focuses on developer and engineering USB peripherals, initially USB serial adapters and logic analyzers across Windows, macOS, and Ubuntu on `x86_64` and `arm64`.

## Repository layout

```text
apps/web/                     Next.js product shell
pipeline/compatforge_pipeline Python identity/evidence tooling
dbt/compatforge/               DuckDB/dbt identity + evidence transformations
data/sources/                  reviewed upstream-source contracts
data/evidence/                 reviewed support statements and observations
data/fixtures/                 public synthetic contract fixtures
tests/fixtures/evidence/       synthetic evidence pipeline fixtures
schemas/                       public JSON Schema contracts
tests/                         contract, resolver, and pipeline tests
docs/                          architecture, data, evidence, privacy, roadmap
.github/workflows/             CI and reviewed refresh workflows
```

## Validate contracts

Python 3.13+:

```bash
python -m pip install -e ".[dev]"
python -m compatforge_pipeline.validate data/fixtures data/evidence/vendor data/evidence/observations
pytest -q
ruff check pipeline tests
```

## Build the identity + evidence platform locally

```bash
python -m pip install -e ".[dev,data]"

python -m compatforge_pipeline.identity_pipeline bronze \
  --workspace build/local \
  --input tests/fixtures/usb.ids \
  --retrieved-at 2026-01-01T00:00:00Z \
  --source-url synthetic://tests/fixtures/usb.ids

python -m compatforge_pipeline.evidence_pipeline ingest \
  --workspace build/local \
  --observations tests/fixtures/evidence/observations \
  --support tests/fixtures/evidence/support \
  --as-of 2026-09-07T00:00:00Z

export COMPATFORGE_DUCKDB_PATH="$PWD/build/local/compatforge.duckdb"
dbt build --project-dir dbt/compatforge --profiles-dir dbt/compatforge
python -m compatforge_pipeline.identity_pipeline snapshot --workspace build/local
python -m compatforge_pipeline.evidence_pipeline snapshot --workspace build/local
```

See [`docs/EVIDENCE_DATA_PLATFORM.md`](docs/EVIDENCE_DATA_PLATFORM.md) for the Bronze -> dbt -> public snapshot design.

## Resolve a compatibility query

```bash
python -m compatforge_pipeline.resolver \
  --query tests/queries/saleae-win11-x64.json \
  --observations data/evidence/observations \
  --support data/evidence/vendor
```

The resolver returns two separate answers: an observed claim and a vendor/support state. Vendor documentation can produce `supported`, but it cannot manufacture an observed `works` result.

See [`docs/RESOLVER.md`](docs/RESOLVER.md) and [`docs/EVIDENCE_MODEL.md`](docs/EVIDENCE_MODEL.md).

## Run the web shell

From `apps/web`:

```bash
npm ci
npm run dev
```

## Project principles

1. Unknown is a valid result.
2. Evidence and derived claims are separate records.
3. Hardware identity and compatibility outcomes are separate data domains.
4. Vendor support and reproduced compatibility are separate evidence classes.
5. Missing configuration facts remain explicit unknowns rather than assumptions.
6. Compatibility specificity must never be silently broadened.
7. Conflicting evidence is preserved, not averaged away.
8. Raw source provenance and licensing are release requirements.
9. Diagnostic collection must be inspectable and privacy-minimized.

## License

Project source code is MIT licensed. Third-party source data keeps its upstream license and attribution requirements; see `THIRD_PARTY_NOTICES.md` and per-snapshot manifests.
