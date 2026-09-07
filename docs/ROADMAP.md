# Roadmap

## Phase 1 - Foundation and data contracts

Status: **complete**.

- repository architecture and scope;
- canonical USB identities;
- device and observation JSON Schemas;
- evidence vocabulary;
- synthetic fixtures;
- validation CLI/tests;
- initial Next.js shell;
- CI and dependency lock review.

## Phase 2 - Hardware identity data platform

Status: **complete**.

- reviewed USB registry ingestion;
- content-addressed raw-source manifests with hashes/licenses/timestamps;
- deterministic normalization;
- Bronze Parquet and DuckDB analytical layer;
- dbt staging/intermediate/mart models and tests;
- deterministic JSONL/Parquet public identity snapshot;
- scheduled read-only refresh candidate workflow;
- double-build reproducibility gate in CI.

## Phase 3 - Compatibility evidence and resolver

Status: **active**.

### Phase 3A - evidence semantics and deterministic resolver

Status: **complete**.

- separate exact observations from scoped vendor/support statements;
- add reviewed Saleae and FTDI support records from official documentation;
- preserve observed claim states without converting vendor support into `works`;
- exact-match resolution;
- explicit host and OS-version relaxation tiers;
- deterministic conflict handling;
- claim-to-observation and support-to-source provenance;
- CLI and regression tests.

### Phase 3B - normalized evidence data platform

Status: **implementation in review**.

- ingest observations/support statements into DuckDB;
- normalize host, OS, driver, software, and connection dimensions with dbt;
- deterministic freshness/staleness models;
- preserve reviewed real-world reproductions without inventing missing connection topology;
- deterministic evidence snapshot export to JSONL/Parquet;
- per-device coverage metrics;
- double-build evidence reproducibility CI.

Phase 3 is complete once Phase 3B is merged with all data-contract, dbt, reproducibility, resolver, and web gates green.

## Phase 4 - Public web MVP

- device catalog/search;
- configuration builder;
- compatibility result pages;
- evidence timelines;
- methodology/coverage pages;
- preview and production deployment.

Target: first stable read-only `v0.1.0`.

## Phase 5 - Local diagnostic agent

- privacy-minimized host/device detection;
- local knowledge snapshot lookup;
- inspectable diagnostic JSON;
- optional user-approved evidence contribution.

## Phase 6 - Community evidence

- authenticated submissions;
- PostgreSQL/Supabase moderation store;
- row-level security;
- validation/review/publish lifecycle;
- abuse and duplicate controls.

## Phase 7 - Coverage and freshness

- scheduled upstream checks;
- additional permitted vendor adapters;
- change reports;
- coverage analytics;
- stale-evidence workflows.

## Phase 8 - Release hardening

- browser acceptance tests;
- security/dependency gates;
- SBOM and checksums;
- immutable data release manifests;
- artifact attestations;
- release candidate and `v1.0.0` acceptance.
