# Architecture

## Goal

CompatForge is an evidence system first and a recommendation interface second. The architecture keeps source evidence reproducible and separates it from derived compatibility claims.

## Planned data flow

```text
open registries / vendor evidence / reviewed observations
                         |
                         v
                 Python ingestion
                         |
                         v
                   raw / bronze
                         |
                         v
         normalization + entity resolution
                         |
                         v
                analytical models
                         |
                         v
              compatibility resolver
                         |
                         +--> immutable release snapshot
                         |          |
                         |          +--> JSON web index
                         |          +--> Parquet analytical data
                         |          +--> manifest/checksums
                         |
                         v
                    Next.js web
```

## Phase 1 boundary

Phase 1 implements only:

- identity helpers;
- public device/observation contracts;
- synthetic validation fixtures;
- validation tooling;
- a non-claiming web shell;
- CI.

There is no scraper, external database, compatibility resolver, account system, or AI component in this phase.

## Design rules

1. Raw observations are immutable evidence records.
2. Derived claims are rebuildable outputs, never hand-edited source facts.
3. Source type does not automatically determine truth.
4. Configuration specificity is explicit.
5. Data releases must be reproducible from identified inputs and parser versions.
6. The public read path should eventually work from an immutable release snapshot without requiring a live application database.
