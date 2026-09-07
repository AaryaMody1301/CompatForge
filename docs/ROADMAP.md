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

Status: **complete**.

- separate observations from scoped vendor/support statements;
- reviewed Saleae and FTDI support evidence;
- reviewed real-world FT232R/Windows ARM64 reproduction with explicit unknown topology;
- exact, host-relaxed, and OS-version-relaxed observation resolution;
- deterministic conflict handling;
- DuckDB evidence ingestion;
- normalized dbt host/OS/driver/software/connection dimensions and fact tables;
- deterministic freshness/staleness models;
- deterministic evidence snapshot export;
- per-device coverage metrics;
- double-build evidence reproducibility CI.

## Phase 4 - Public web MVP

Status: **complete**.

- searchable reviewed device catalog;
- static device evidence pages;
- configuration-level compatibility checker;
- separate observed-compatibility and vendor-support results;
- explicit resolver-relaxation labels;
- evidence sources and device timelines;
- coverage and methodology pages;
- responsive/accessibility-focused UI;
- Vercel production deployment verified against the merged commit.

## Phase 5 - Local diagnostic agent

Status: **active**.

Phase 5A implements:

- privacy-minimized host/OS/architecture detection;
- target-only USB presence detection on Windows, macOS, and Linux;
- canonical diagnostic-manifest JSON Schema;
- explicit no-upload/no-serial/no-network privacy flags;
- Linux USB hub/direct-path classification and link speed when available;
- inspectable `compatforge-diagnose` CLI output;
- synthetic parser/contract tests;
- cross-platform host-only CI smoke tests.

Remaining Phase 5 work:

- privacy-reviewed driver-version collection;
- packaged local CompatForge snapshot lookup;
- local resolver explanation using the diagnostic manifest;
- signed/packageable CLI release artifacts;
- user-approved contribution handoff, without automatic upload.

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
