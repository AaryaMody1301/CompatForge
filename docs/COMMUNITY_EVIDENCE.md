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

A community submission has `evidence_ready: false`. Publication requires a separate reviewed conversion into the canonical `compatibility_observation` evidence model. The moderation database never rewrites the original user payload into a stronger claim.

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

## PostgreSQL/Supabase layout

Phase 6A adds a version-controlled local Supabase project and migration.

### Public API surface

`public.evidence_submissions` is a private queue despite living in the API-exposed `public` schema. Row Level Security is enabled. Authenticated users may only read their own rows; moderators may read all rows through a narrowly scoped security-definer membership check.

Direct client `INSERT`, `UPDATE`, and `DELETE` privileges are revoked. Authenticated creation goes through `public.submit_community_evidence(jsonb)`, which enforces critical privacy and contract invariants before inserting the row.

### Private moderation surface

The non-exposed `private` schema contains:

- `moderator_memberships`;
- `submission_moderation` validation, duplicate and decision metadata;
- append-only `submission_state_events` for lifecycle history.

Authenticated/anonymous roles receive no direct table privileges in this schema.

## Lifecycle rules

The database accepts only these forward transitions:

- `submitted -> validated | rejected`
- `validated -> pending_review | rejected`
- `pending_review -> accepted | rejected`
- `accepted -> published | rejected`

`published` and `rejected` are terminal in Phase 6A. A published row must reference the canonical observation created by the reviewed publication step.

## Duplicate and abuse controls

Each user/client submission ID is unique. The database stores SHA-256 hashes and a semantic duplicate-candidate fingerprint, and indexes fingerprints for moderation. A matching fingerprint is a review signal, not an automatic rejection: independent users can legitimately reproduce the same configuration.

Rate limits, authenticated web/API integration and moderation tooling are Phase 6B/6C work.

## Local verification

Phase 6 uses the Supabase CLI and pgTAP:

```bash
supabase db start
supabase db lint --local --level error
supabase test db
```

The committed CI workflow pins Supabase CLI `2.117.0`. Tests verify RLS is enabled, anonymous access is denied, direct mutation is denied, the authenticated submission RPC is the write surface, private moderation tables stay private, and lifecycle transitions are constrained.

## Secret-key boundary

Future server-side moderation may use a Supabase secret/service role, which bypasses RLS. Such keys must remain server-side and must never be exposed to the browser. Client access uses authenticated JWTs plus RLS.
