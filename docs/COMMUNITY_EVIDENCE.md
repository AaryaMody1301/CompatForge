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

Phase 6A established the version-controlled local Supabase project and moderation queue. Phase 6B adds database-enforced abuse controls and the bounded dashboard API consumed by the authenticated web product.

### Public API surface

`public.evidence_submissions` is a private queue despite living in the API-exposed `public` schema. Row Level Security is enabled. Authenticated users may only read their own rows; moderators may read all rows through a narrowly scoped security-definer membership check.

Direct client `INSERT`, `UPDATE`, and `DELETE` privileges are revoked. Authenticated creation goes through `public.submit_community_evidence(jsonb)`, which enforces critical privacy and contract invariants before inserting the row.

`public.get_my_submission_dashboard()` returns only the current user's submissions plus an opaque `duplicate_candidate` boolean. It does not expose another user's payload, identity, timestamps, or outcome.

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

`published` and `rejected` are terminal. A published row must reference the canonical observation created by the reviewed publication step.

## Duplicate and abuse controls

Each user/client submission ID is unique. The database stores SHA-256 hashes and a semantic duplicate-candidate fingerprint, and indexes fingerprints for moderation. A matching fingerprint is a review signal, not an automatic rejection: independent users can legitimately reproduce the same configuration.

Phase 6B enforces limits at the database boundary so a caller cannot bypass them by skipping the website:

- maximum 5 submissions per authenticated user in a rolling hour;
- maximum 20 submissions per authenticated user in a rolling 24-hour window;
- existing 64 KiB payload and bounded-array limits remain in force.

When a newly inserted fingerprint matches a non-rejected submission, moderation metadata receives a `duplicate_candidate` risk flag. The user's dashboard sees only the boolean duplicate signal.

## Authenticated web boundary

Phase 6B uses Supabase Auth with GitHub OAuth and cookie-based SSR. The website never stores a GitHub provider token. OAuth establishes the Supabase user identity used by `auth.uid()` and RLS; all submission authorization is rechecked in the database rather than trusting a browser or Proxy redirect.

The web form accepts only normalized, allowlisted fields from the community-submission contract. It does not accept raw diagnostic uploads. Server-side parsing constructs the final JSON payload and calls the validated database RPC.

## Local verification

Phase 6 uses the Supabase CLI and pgTAP:

```bash
supabase db start
supabase db lint --local --level error
supabase test db
```

The committed CI workflow pins Supabase CLI `2.117.0`. Tests verify RLS is enabled, anonymous access is denied, direct mutation is denied, the authenticated submission RPC is the write surface, private moderation tables stay private, lifecycle transitions are constrained, rate limiting is database-enforced, duplicate candidates are moderation-only signals, and the dashboard RPC is authenticated-only.

## Secret-key boundary

Future server-side moderation may use a Supabase secret/service role, which bypasses RLS. Such keys must remain server-side and must never be exposed to the browser. Phase 6B needs only the public/publishable Supabase key because user-scoped reads and writes are governed by JWTs plus RLS/RPC validation.
