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

### Phase 5A - privacy-first collection foundation

Status: **complete**.

- privacy-minimized host/OS/architecture detection;
- target-only USB presence detection on Windows, macOS, and Linux;
- canonical diagnostic-manifest JSON Schema;
- explicit no-upload/no-serial/no-network privacy flags;
- Linux USB hub/direct-path classification and link speed when available;
- inspectable diagnostic output;
- synthetic parser/contract tests;
- cross-platform host-only CI smoke tests.

### Phase 5B - offline context and explanation

Status: **complete**.

- privacy-reviewed target driver metadata on Windows and Linux;
- explicit unavailable driver state on macOS rather than broad collection;
- deterministic packaged local compatibility snapshot;
- snapshot drift verification against reviewed repository evidence;
- offline explanation using the existing deterministic resolver;
- source/limitation provenance in local explanations;
- snapshot SHA-256 and record counts in every explanation;
- no upload or network dependency.

### Phase 5C - distributable release and explicit handoff

Status: **active**.

- unified `compatforge-hw` end-user CLI;
- packaged JSON Schema contracts for source-independent/frozen validation;
- explicit `--approve-export` contribution handoff with `evidence_ready: false`;
- native standalone builds for Linux, Windows, and macOS on x86_64/arm64;
- SPDX SBOMs and SHA-256 release manifests;
- GitHub provenance and SBOM attestations outside pull requests;
- pull-request smoke verification of frozen binaries;
- end-user installation, verification, and signing-boundary documentation;
- no automatic upload.

Phase 5 is complete once Phase 5C's cross-platform release workflow is green and the first release-candidate process has been audited. Native Apple notarization and Windows Authenticode are not falsely claimed by provenance attestations.

## Phase 6 - Community evidence

- authenticated submissions;
- PostgreSQL/Supabase moderation store;
- row-level security;
- validation/review/publish lifecycle;
- abuse and duplicate controls;
- explicit conversion of reviewed handoff context into evidence only after user-supplied outcome/reproduction details.

## Phase 7 - Coverage and freshness

- scheduled upstream checks;
- additional permitted vendor adapters;
- change reports;
- coverage analytics;
- stale-evidence workflows.

## Phase 8 - Release hardening

- browser acceptance tests;
- security/dependency gates;
- immutable data release manifests;
- artifact attestations across web/data release surfaces;
- release candidate and `v1.0.0` acceptance.
