# Evidence data platform

Phase 3B turns reviewed compatibility evidence into a reproducible analytical dataset without changing the evidence semantics established in Phase 3A.

## Data flow

```text
validated observations + support statements
                  |
                  v
        evidence_pipeline ingest
                  |
                  v
       DuckDB bronze evidence tables
                  |
                  v
                dbt
        /          |          \
 dimensions      facts      freshness
        \          |          /
                  v
           evidence_coverage
                  |
                  v
     deterministic JSONL + Parquet
```

## Bronze tables

`bronze.compatibility_observations` contains one flattened row per validated observation. Nested paths, conditions, and limitations remain canonical JSON strings so the original record is reconstructable from the source corpus.

`bronze.support_statements` contains one flattened row per scoped support statement.

`bronze.evidence_run_metadata` stores the explicit `as_of` timestamp used for all freshness calculations. CI never uses the wall clock for snapshot semantics.

Every Bronze evidence row has a canonical `record_sha256` calculated from the validated JSON document.

## Dimensions

The dbt layer builds normalized dimensions for hosts, operating systems, drivers, software, and connection paths. Facts keep their source IDs and record hashes so every exported row maps back to its original reviewed evidence record.

## Freshness

Freshness is deterministic relative to the evidence snapshot `as_of` timestamp:

- `fresh`: 0-180 days old;
- `aging`: 181-365 days old;
- `stale`: more than 365 days old.

Evidence dated after the snapshot reference time fails a dbt singular test.

Freshness never changes an observation outcome or support state. It is metadata shown beside the evidence.

## Coverage

`analytics.evidence_coverage` exposes per-device counts for observations, support statements, covered OS families and architectures, stale evidence, and a coarse coverage state:

- `observed_and_supported`
- `observed_only`
- `support_only`
- `unknown`

An `unknown` coverage state is useful product data; it is not treated as an error.

## Public evidence snapshot

The evidence exporter writes:

```text
public/evidence/
├── compatibility_observations.jsonl
├── compatibility_observations.parquet
├── support_statements.jsonl
├── support_statements.parquet
├── evidence_coverage.jsonl
├── evidence_coverage.parquet
└── snapshot_manifest.json
```

The manifest contains the input evidence hash, explicit `as_of` timestamp, row counts, per-file SHA-256 hashes, and a canonical snapshot hash. CI builds the same synthetic corpus twice and requires byte-level artifact hashes to match.
