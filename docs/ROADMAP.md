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

Status: **implementation complete; hosted acceptance pending configuration**.

### Phase 6A - submission and moderation foundation

Status: **complete**.

- bounded `community_evidence_submission` public contract;
- deterministic duplicate-candidate fingerprinting;
- version-controlled Supabase/PostgreSQL migration;
- authenticated submission RPC with critical privacy checks;
- RLS-protected submitter reads;
- private moderator membership, decision metadata and lifecycle event tables;
- deterministic lifecycle transition guard;
- pgTAP RLS/schema tests in CI.

### Phase 6B - authenticated product integration

Status: **complete**.

- GitHub OAuth through Supabase Auth with a PKCE callback route;
- cookie-based Next.js SSR session refresh;
- authorization rechecks in server actions/routes plus database RLS;
- authenticated submission/status UI;
- server-side allowlist parsing plus Draft 2020-12 JSON Schema validation;
- database-enforced rolling limits of 5 submissions/hour and 20/24 hours per user;
- moderation-only duplicate-candidate flags with an opaque submitter-facing signal;
- no raw diagnostic upload, provider-token persistence, automatic publication, or service-role key in the web app.

Hosted Supabase/GitHub provider configuration and end-to-end OAuth acceptance remain deployment gates documented in `docs/AUTH_SETUP.md`.

### Phase 6C - moderation and publication

Status: **complete**.

- bounded moderator queue and per-submission review surface that omit submitter identity;
- reviewer/admin membership checked again at the PostgreSQL boundary;
- public security-invoker RPC wrappers over private, search-path-pinned security-definer implementations;
- validation, pending-review, acceptance and rejection actions with append-only audit reasons;
- deterministic canonicalization blockers for reports that do not satisfy the stricter `compatibility_observation` contract;
- immutable accepted observation candidates with observation SHA-256 and source-payload SHA-256 provenance;
- repository-backed canonical evidence URLs that become resolvable through the reviewed static-snapshot merge;
- admin-only publication receipt requiring the exact accepted candidate hash plus the full merged static-snapshot commit SHA;
- explicit separation between database acceptance and public static evidence publication;
- clean-room pgTAP coverage for least privilege, canonicalization, determinism, hashing and publication gates;
- moderator bootstrap and operating procedure in `docs/MODERATION.md`.

Hosted moderator acceptance still requires a configured Supabase project, at least one allowlisted moderator membership, and a real reviewed publication cycle. Phase 6C does not introduce a service-role key into the web product or auto-write database records into GitHub.

## Phase 7 - Coverage and freshness

Status: **complete**.

### Phase 7A - freshness and source-health review

Status: **complete**.

- scheduled read-only upstream source checks;
- deterministic evidence freshness and per-device coverage reports;
- aging/stale review queues using the existing 180/365-day analytical thresholds;
- exact evidence/source references and report SHA-256 provenance;
- bounded source status/final-URL/ETag/Last-Modified signals;
- no automatic evidence mutation or publication.

### Phase 7B - permitted vendor adapters and semantic change reports

Status: **complete**.

- exact-host HTTPS allowlisting for source-specific vendor adapters;
- bounded FTDI VCP semantic extraction;
- bounded Saleae supported-OS semantic extraction;
- version-controlled reviewed semantic baselines without mirroring vendor pages;
- semantic SHA-256 comparison that ignores irrelevant HTML/template churn;
- exact changed-field reporting;
- integration with the weekly Phase 7 review artifact workflow;
- review-only output with no canonical evidence rewrite.

### Phase 7C - accepted-community refresh preparation

Status: **complete**.

- dedicated least-privilege refresh identities separate from reviewer/admin membership;
- bounded accepted/unpublished refresh RPC returning both candidate JSON and its exact hashed PostgreSQL text;
- byte-for-byte candidate materialization so repository file SHA-256 equals the immutable accepted candidate SHA-256;
- collision refusal instead of overwriting existing canonical evidence;
- deterministic refresh manifests with candidate and source-payload provenance;
- CI verification of refresh manifests and exact candidate bytes;
- scheduled/manual bot-owned refresh branch and pull-request preparation;
- separate GitHub App/fine-grained token path so automation-created PRs can trigger normal CI;
- no database-to-main direct write, automatic merge, or automatic publication receipt.

Hosted acceptance requires the Phase 7C Supabase automation identity and GitHub refresh token described in `docs/COMMUNITY_REFRESH_AUTOMATION.md`.

### Phase 7D - coverage and stale-evidence operations

Status: **complete**.

- deterministic OS-family/architecture coverage matrix per reviewed device;
- observed, vendor-supported, corroborated and vendor-only reproduction-gap counts;
- deterministic `P0`-`P3` work queue combining age, source health and semantic-change signals;
- explicit source-health, stale/aging evidence, vendor-change and reproduction-gap task types;
- combined weekly Markdown review dashboard and JSON operations artifact;
- report SHA-256 provenance over the operations output;
- FTDI D2XX exact-host adapter covering reviewed Windows, Linux and macOS driver facts;
- reviewed D2XX semantic baseline without mirroring vendor HTML;
- no automatic canonical evidence mutation or publication.

Phase 7D scoring is review triage only. Detailed semantics and local commands are documented in `docs/EVIDENCE_OPERATIONS.md`.

## Phase 8 - Release hardening

Status: **implementation in progress**.

### Phase 8A - browser acceptance

Status: **implementation complete; merge pending**.

- real headless-Chrome acceptance against the exact production Next.js build in pull-request CI;
- no new web testing dependency or package-lock expansion;
- reviewed home, search, device detail, checker, coverage, contribution-entry and custom-404 routes;
- HTTP-status and browser-rendered DOM assertions with runtime-error marker rejection;
- desktop, narrow/mobile and compatibility-result screenshots as review artifacts;
- JSON and Markdown acceptance reports retained with the CI run;
- scheduled/manual browser smoke against the stable Vercel production alias with a public URL override;
- read-only workflow permissions and no automated OAuth, evidence mutation, deployment or publication.

See `docs/BROWSER_ACCEPTANCE.md` for the exact contract and local commands.

### Phase 8B - supply-chain and security gates

- dependency-review enforcement for pull requests;
- dependency and workflow security policy;
- production security-header acceptance;
- secret and high-severity vulnerability gates where supported by the public repository/tooling boundary.

### Phase 8C - immutable release manifests and attestations

- immutable identity/evidence release manifest tying reviewed data to source commits and hashes;
- web/data release artifact provenance;
- expanded attestations beyond the existing hardware CLI surface;
- release-manifest verification commands and CI gates.

### Phase 8D - release candidate and v1.0.0 acceptance

- resolve remaining hosted acceptance/configuration gates;
- verify repository release immutability settings;
- cut and verify release candidates;
- document rollback and release acceptance;
- publish `v1.0.0` only after every required gate is green.
