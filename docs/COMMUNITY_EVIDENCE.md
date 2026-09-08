# Community evidence

Phase 6 introduces authenticated community submissions without allowing a user report to become public compatibility evidence automatically.

## Trust boundary

The lifecycle is:

```text
approved local handoff
        +
user-supplied reproduction details
        |
        v
community_evidence_submission
        |
        v
SUBMITTED -> VALIDATED -> PENDING_REVIEW -> ACCEPTED -> PUBLISHED
       \          \             \             \
        +----------+-------------+---------------> REJECTED
```

A community submission has `evidence_ready: false`. Publication requires a separate reviewed conversion into the canonical `compatibility_observation` evidence model plus proof that the exact accepted candidate was merged into the reviewed static snapshot. The moderation database never rewrites the original user payload into a stronger claim.

## Submission contract

`schemas/community-submission.schema.json` requires:

- a canonical USB device ID;
- an explicitly approved Phase 5 contribution handoff hash;
- host, OS, architecture, connection path and bounded driver context;
- exactly one observed reproduction outcome: `works`, `works_with_conditions`, or `fails`;
- an observation timestamp and human-readable reproduction summary;
- explicit limitations;
- anonymized-publication consent;
- privacy flags proving raw diagnostics, serials, network identifiers and unrelated USB inventory are absent.

`unknown` and `conflicting` are not valid user observation outcomes. They remain resolver/claim states.

The community contract is intentionally more permissive than the canonical observation contract. For example, a user may submit an unknown architecture or omit the host model for review, but those values block canonical publication rather than being silently inferred.

## PostgreSQL/Supabase layout

Phase 6A established the version-controlled local Supabase project and moderation queue. Phase 6B added database-enforced abuse controls and the bounded submitter dashboard API. Phase 6C adds moderator review and publication gates.

### Public API surface

`public.evidence_submissions` is a private queue despite living in the API-exposed `public` schema. Row Level Security is enabled. Authenticated submitters may directly read only their own rows.

Phase 6C removes the previous moderator-wide direct RLS read. Moderators use bounded RPCs instead, so the normal review product does not expose submitter identity or grant broad direct table access.

Direct client `INSERT`, `UPDATE`, and `DELETE` privileges remain revoked. Authenticated creation goes through `public.submit_community_evidence(jsonb)`, which is now a security-invoker wrapper around a non-exposed private implementation that enforces critical privacy and contract invariants.

`public.get_my_submission_dashboard()` remains bounded to the current user's submissions plus an opaque `duplicate_candidate` boolean. It does not expose another user's payload, identity, timestamps, or outcome.

Moderator-facing public RPCs are also security-invoker wrappers. Privileged implementations live in the non-exposed `private` schema as `SECURITY DEFINER` functions with `search_path = ''` and schema-qualified object references.

### Private moderation surface

The non-exposed `private` schema contains:

- `moderator_memberships`;
- `submission_moderation` validation, duplicate and decision metadata;
- append-only `submission_state_events` for lifecycle history;
- `community_observation_candidates` for immutable accepted canonical candidates and publication receipts.

Authenticated/anonymous roles receive no direct table privileges in this schema.

## Lifecycle rules

The database accepts only these forward transitions:

- `submitted -> validated | rejected`
- `validated -> pending_review | rejected`
- `pending_review -> accepted | rejected`
- `accepted -> published | rejected`

`published` and `rejected` are terminal. A published row must reference the canonical observation created by the reviewed publication process.

Phase 6C records the moderator/admin reason on lifecycle transitions. Acceptance and rejection require explicit decision reasons.

## Canonicalization and acceptance

Validation evaluates whether the private community payload can be represented faithfully by `schemas/observation.schema.json`. Publication blockers include missing required host identity, unsupported/unknown canonical OS or architecture values, overlong canonical strings, and incomplete driver metadata.

A report may move into human review with blockers, but acceptance fails while blockers remain. Reviewers cannot fill missing facts by inventing values during conversion.

Acceptance creates exactly one immutable candidate in `private.community_observation_candidates` containing:

- deterministic `obs_community_<submission UUID without hyphens>` observation ID;
- canonical observation JSON;
- SHA-256 of the exact observation candidate;
- SHA-256 of the original private submission payload;
- private reviewer/time provenance.

The public candidate contains no submitter ID. It is explicitly labeled `community_report` and preserves source-payload provenance by hash.

## Publication gate

Acceptance is not publication.

CompatForge's public compatibility product remains based on reviewed Git/static snapshot artifacts. An accepted candidate becomes `published` only after the exact candidate has been added to the reviewed static evidence input, passed the normal evidence/data/web CI, and been merged.

The admin publication RPC requires the accepted candidate's exact SHA-256, the full 40-character merged snapshot commit SHA, and an authenticated user whose private moderator role is `admin`.

PostgreSQL compares the expected candidate hash against the frozen accepted candidate before recording publication. The publication receipt stores the snapshot commit SHA, sets `published_observation_id`, and transitions the source submission to `published`.

A database state change therefore cannot substitute for a reviewed static-snapshot merge. Phase 7 may automate creation of accepted-candidate refresh PRs, but it must preserve this review/hash/merge boundary.

See `docs/MODERATION.md` for the operating procedure and moderator bootstrap.

## Duplicate and abuse controls

Each user/client submission ID is unique. The database stores SHA-256 hashes and a semantic duplicate-candidate fingerprint, and indexes fingerprints for moderation. A matching fingerprint is a review signal, not an automatic rejection: independent users can legitimately reproduce the same configuration.

Phase 6B enforces limits at the database boundary so a caller cannot bypass them by skipping the website:

- maximum 5 submissions per authenticated user in a rolling hour;
- maximum 20 submissions per authenticated user in a rolling 24-hour window;
- existing 64 KiB payload and bounded-array limits remain in force.

When a newly inserted fingerprint matches a non-rejected submission, moderation metadata receives a `duplicate_candidate` risk flag. The user's dashboard sees only the boolean duplicate signal.

## Authenticated web boundary

Phase 6B uses Supabase Auth with GitHub OAuth and cookie-based SSR. The website never stores a GitHub provider token. OAuth establishes the Supabase user identity used by `auth.uid()` and RLS/RPC authorization.

Phase 6C reuses that session for moderator pages, but authentication alone never grants moderator authority. Every moderator action is re-authorized in PostgreSQL against `private.moderator_memberships`.

The submission form accepts only normalized, allowlisted fields from the community-submission contract. It does not accept raw diagnostic uploads. Moderator pages display only that normalized private payload and bounded moderation metadata.

No service-role/secret Supabase key is introduced into the Next.js web product.

## Local verification

Phase 6 uses the Supabase CLI and pgTAP:

```bash
supabase db start
supabase db lint --local --level error
supabase test db
```

The committed CI workflow pins Supabase CLI `2.117.0`. Tests cover RLS, anonymous denial, direct mutation denial, private-table isolation, lifecycle transitions, rate limiting, duplicate signals, bounded submitter access, least-privilege moderator RPC structure, canonicalization blockers, deterministic observation construction, candidate hashing, admin-only publication, and transition-reason auditing.

## Operational boundaries

Hosted GitHub OAuth acceptance requires the deployment configuration described in `docs/AUTH_SETUP.md`.

Hosted moderation acceptance additionally requires at least one real Supabase user to be inserted into `private.moderator_memberships`, followed by a real review and static-snapshot publication cycle. Local CI verifies the contracts and authorization structure, but does not falsely claim those hosted steps have occurred.
