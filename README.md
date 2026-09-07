# CompatForge

Evidence-first hardware compatibility intelligence.

CompatForge answers a narrow but difficult question:

> Will this peripheral work with this host, operating system, architecture, driver, firmware, and connection path - and what evidence supports that answer?

The project treats compatibility as a configuration-level evidence problem rather than a binary device-to-laptop lookup. Missing evidence stays `UNKNOWN`; conflicting evidence stays visible; vendor support is never rewritten into a reproduced success.

## Current build status

**Phase 1 - foundation and evidence contracts:** complete.

**Phase 2 - hardware identity data platform:** complete. The repository has reviewed USB identity ingestion, content-addressed raw snapshots, source manifests, Bronze Parquet/DuckDB tables, dbt staging/intermediate/mart models, deterministic public snapshot export, and scheduled refresh candidates.

**Phase 3 - compatibility evidence and resolver:** complete. Reviewed support statements and observations flow through DuckDB/dbt evidence models, deterministic freshness/coverage marts, public evidence snapshots, and a resolver that keeps observed compatibility separate from vendor support.

**Phase 4 - public web MVP:** complete and deployed on Vercel.

**Phase 5 - local diagnostic agent:** active. Phase 5A established privacy-first cross-platform collection. Phase 5B adds target-scoped driver context, a deterministic packaged compatibility snapshot, and offline resolver explanations.

## Initial scope

The first public compatibility release focuses on developer and engineering USB peripherals, initially USB serial adapters and logic analyzers across Windows, macOS, and Ubuntu on `x86_64` and `arm64`.

## Repository layout

```text
apps/web/                     Next.js public product
pipeline/compatforge_pipeline Python identity/evidence/local-agent tooling
dbt/compatforge/               DuckDB/dbt identity + evidence transformations
data/sources/                  reviewed upstream-source contracts
data/evidence/                 reviewed support statements and observations
data/fixtures/                 public synthetic contract fixtures
tests/fixtures/evidence/       synthetic evidence pipeline fixtures
schemas/                       public JSON Schema contracts
tests/                         contract, resolver, diagnostic, and pipeline tests
docs/                          architecture, evidence, web, privacy, roadmap
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

See [`docs/EVIDENCE_DATA_PLATFORM.md`](docs/EVIDENCE_DATA_PLATFORM.md).

## Resolve a compatibility query

```bash
python -m compatforge_pipeline.resolver \
  --query tests/queries/saleae-win11-x64.json \
  --observations data/evidence/observations \
  --support data/evidence/vendor
```

The resolver returns two separate answers: an observed claim and a vendor/support state.

## Run the local diagnostic workflow

```bash
compatforge-diagnose \
  --device usb:0403:6001 \
  --output compatforge-diagnostic.json

compatforge-explain \
  --diagnostic compatforge-diagnostic.json \
  --output compatforge-explanation.json

compatforge-snapshot info
```

Both commands run locally. The diagnostic manifest contains allowlisted machine facts; the explanation is a separate derived record backed by the packaged reviewed snapshot. Neither command uploads data. See [`docs/DIAGNOSTIC_AGENT.md`](docs/DIAGNOSTIC_AGENT.md).

## Run the public web MVP

From `apps/web`:

```bash
npm ci
npm run dev
```

The web app imports the reviewed JSON evidence directly from `data/evidence/`; it does not require a live database or paid API. See [`docs/WEB_MVP.md`](docs/WEB_MVP.md).

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
