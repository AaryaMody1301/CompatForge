# CompatForge

Evidence-first hardware compatibility intelligence for developer USB peripherals.

CompatForge answers a configuration-level question:

> Will this peripheral work with this host, operating system, architecture, driver, firmware, and connection path — and what evidence supports that answer?

A known USB identity is not a compatibility claim. Missing evidence stays `UNKNOWN`, conflicting evidence stays visible, and vendor support is kept separate from reproduced observations.

## Release preview status

The implementation roadmap through Phase 8 is complete. The repository now includes:

- deterministic USB identity ingestion and reviewed release-preview catalog data;
- reviewed compatibility evidence with explicit provenance and freshness;
- a deterministic compatibility resolver;
- a Next.js web product with browser acceptance and production security-header checks;
- a privacy-minimized cross-platform diagnostic CLI with six native build targets;
- authenticated community submission, moderation, and controlled publication contracts;
- scheduled source-health, vendor-change, coverage, and refresh operations;
- dependency audits, CodeQL, SBOMs, immutable release manifests, attestations, and release acceptance gates.

The first `v1.0.0-rc.1` tag remains intentionally uncreated until the external release-acceptance settings documented in [`docs/RELEASE_ACCEPTANCE.md`](docs/RELEASE_ACCEPTANCE.md) are green.

## Device coverage

The release-preview web catalog contains known developer-device identities separately from compatibility evidence. Identity-only devices can be searched and checked, but they return unknown compatibility until reviewed support statements or observations exist.

The current preview catalog covers FTDI FT232/FT2232/FT4232/FT232H, Silicon Labs CP210x/CP2105/CP2108, QinHeng CH340/CH341, and Saleae Logic Pro 8. The identity refresh pipeline uses the upstream USB ID Repository to prepare broader deterministic candidates for review.

## Repository layout

```text
apps/web/                     Next.js web product
pipeline/compatforge_pipeline Python identity, evidence, diagnostics, and release tooling
dbt/compatforge/              DuckDB/dbt transformations
data/catalog/                 reviewed web identity catalog
data/sources/                 upstream-source contracts and vendor baselines
data/evidence/                reviewed support statements and observations
data/fixtures/                public synthetic contract fixtures
schemas/                      public JSON Schema contracts
supabase/                     database migrations and pgTAP tests
tests/                        Python contract and pipeline tests
tools/                        deterministic packaging helpers
.github/workflows/            CI, security, refresh, and release workflows
docs/                         architecture and operating documentation
```

## Validate the repository

Python 3.13+:

```bash
python -m pip install -e ".[dev,data]"
ruff check pipeline tests
pytest -q
python -m compatforge_pipeline.validate \
  data/fixtures \
  data/evidence/vendor \
  data/evidence/observations
compatforge-snapshot verify \
  --observations data/evidence/observations \
  --support data/evidence/vendor
```

Web:

```bash
cd apps/web
npm ci
npm run lint
npm run typecheck
npm run build
```

The full pull-request matrix additionally runs deterministic data builds, browser acceptance, dependency audits, CodeQL, Supabase migration/RLS tests, release-provenance verification, and all six frozen CLI builds.

## Local diagnostic CLI

```bash
compatforge-hw diagnose \
  --device usb:0403:6001 \
  --output compatforge-diagnostic.json

compatforge-hw explain \
  --diagnostic compatforge-diagnostic.json \
  --output compatforge-explanation.json

compatforge-hw snapshot-info
```

Diagnostics and explanations run locally. Contribution preparation requires explicit export approval and still produces only a local, non-evidence-ready JSON handoff:

```bash
compatforge-hw prepare-contribution \
  --diagnostic compatforge-diagnostic.json \
  --explanation compatforge-explanation.json \
  --approve-export \
  --output contribution-handoff.json
```

See [`docs/DIAGNOSTIC_AGENT.md`](docs/DIAGNOSTIC_AGENT.md), [`docs/PRIVACY.md`](docs/PRIVACY.md), and [`docs/CLI_RELEASE.md`](docs/CLI_RELEASE.md).

## Compatibility resolver

```bash
python -m compatforge_pipeline.resolver \
  --query tests/queries/saleae-win11-x64.json \
  --observations data/evidence/observations \
  --support data/evidence/vendor
```

The resolver returns separate observed-compatibility and vendor-support states.

## Principles

1. Unknown is a valid result.
2. Hardware identity and compatibility evidence are separate data domains.
3. Vendor support and reproduced compatibility are separate evidence classes.
4. Missing configuration facts remain explicit unknowns.
5. Compatibility specificity is never silently broadened.
6. Conflicting evidence is preserved.
7. Provenance and licensing are release requirements.
8. Diagnostic collection is inspectable and privacy-minimized.
9. Database acceptance and public evidence publication are separate actions.
10. Release artifacts are deterministic, hashed, and verified before publication.

## License

Project source code is MIT licensed. Third-party source data retains its upstream license and attribution requirements; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and snapshot manifests.
