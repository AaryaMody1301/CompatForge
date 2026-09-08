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

Status: **implementation complete; first immutable release candidate pending repository-setting audit**.

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

Status: **implementation complete**.

- unified `compatforge-hw` end-user CLI;
- packaged JSON Schema contracts for source-independent/frozen validation;
- explicit `--approve-export` contribution handoff with `evidence_ready: false`;
- native standalone builds for Linux, Windows, and macOS on x86_64/arm64;
- SPDX SBOMs and SHA-256 release manifests;
- GitHub provenance and SBOM attestation workflow;
- pull-request smoke verification of all six frozen binaries;
- end-user installation, verification, and signing-boundary documentation;
- no automatic upload.

The first `hw-cli-v0.3.0rc1` tag remains intentionally uncreated until repository release immutability is confirmed. This operational gate does not weaken or get folded into Phase 6 code.

## Phase 6 - Community evidence

Status: **active**.

### Phase 6A - submission and moderation foundation

- bounded `community_evidence_submission` public contract;
- deterministic duplicate-candidate fingerprinting;
- version-controlled Supabase/PostgreSQL migration;
- authenticated submission RPC with critical privacy checks;
- RLS-protected submitter reads;
- private moderator membership, decision metadata and lifecycle event tables;
- deterministic lifecycle transition guard;
- pgTAP RLS/schema tests in CI.

### Phase 6B - authenticated product integration

- GitHub OAuth through Supabase Auth;
- Next.js server-side session handling;
- submit/review-status UI;
- server-side JSON Schema validation before database submission;
- rate limits and abuse controls;
- duplicate-candidate surfacing.

### Phase 6C - moderation and publication

- moderator review queue;
- validation/reject/accept actions;
- reviewed conversion to canonical `compatibility_observation` records;
- publication provenance linking submission -> moderation -> observation;
- public evidence refresh only after acceptance/publish gates.

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
