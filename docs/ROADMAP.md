# Roadmap

## Phase 1 - Foundation and data contracts

- repository architecture and scope;
- canonical USB identities;
- device and observation JSON Schemas;
- evidence vocabulary;
- synthetic fixtures;
- validation CLI/tests;
- initial Next.js shell;
- CI and dependency lock review.

Merge gate: contracts are tested, web build is green, dependency graph is locked, and no real compatibility claim is published.

## Phase 2 - Hardware identity data platform

- reviewed USB registry ingestion;
- raw-source manifests with hashes/licenses/timestamps;
- normalization and source-freshness checks;
- DuckDB analytical layer;
- dbt staging/intermediate/mart models;
- deterministic data snapshot build.

## Phase 3 - Compatibility evidence and resolver

- reviewed real observations;
- normalized host/OS/driver/connection dimensions;
- exact-match resolution;
- explicit specificity relaxation;
- conflict and staleness handling;
- claim-to-observation provenance.

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
