# Community moderation and publication

Phase 6C turns authenticated community submissions into a controlled review workflow without allowing a database decision to silently become public compatibility evidence.

## Roles

CompatForge keeps moderator membership in `private.moderator_memberships`.

- `reviewer` can validate, move a submission to human review, accept a publishable reproduction, or reject it.
- `admin` has the reviewer capabilities and may additionally record publication after the exact accepted observation has been merged into the reviewed static evidence snapshot.

Authentication and authorization are separate. GitHub OAuth establishes a Supabase user identity. Database membership grants moderation authority.

The normal web application uses only the public/publishable Supabase key plus the signed-in user's JWT. No service-role or secret key is required by the browser or Next.js product surface.

## Moderator bootstrap

An existing database owner or other appropriately privileged operator can add a moderator after that person has signed in once and therefore has an `auth.users` UUID:

```sql
insert into private.moderator_memberships (user_id, role)
values ('<supabase-user-uuid>', 'reviewer')
on conflict (user_id) do update
set role = excluded.role;
```

Use `admin` instead of `reviewer` only for operators who are allowed to attest that a reviewed static evidence snapshot has actually been merged.

Do not expose database owner credentials, service-role credentials, or Supabase secret keys to client-side code.

## Review surface

The moderator product lives at `/moderation`.

Direct moderator-wide reads of `public.evidence_submissions` are intentionally not granted through RLS. The submitter policy remains the only direct row policy. Moderator pages use bounded RPCs that omit submitter identity and expose only the fields needed to review evidence.

The public API functions are security-invoker wrappers. Privileged implementations live in the non-exposed `private` schema as `SECURITY DEFINER` functions with an empty `search_path` and schema-qualified object references.

## Lifecycle

The database preserves the Phase 6 lifecycle:

```text
SUBMITTED -> VALIDATED -> PENDING_REVIEW -> ACCEPTED -> PUBLISHED
       \          \             \             \
        +----------+-------------+---------------> REJECTED
```

The web product maps those transitions to four reviewer actions:

1. **Validate** — re-runs deterministic canonical-publication checks and records blockers in private moderation metadata.
2. **Queue review** — records reviewer assignment and moves a validated report to human review.
3. **Accept** — requires a reason and no canonicalization blockers. Acceptance freezes an immutable canonical observation candidate plus SHA-256.
4. **Reject** — requires an auditable reason and ends the submission lifecycle.

Acceptance is not publication.

## Canonicalization gate

`community_evidence_submission` is intentionally more permissive than `compatibility_observation`. A report can be valid for community review while still being too vague for canonical evidence.

Before acceptance, Phase 6C requires fields that the canonical observation contract needs, including:

- host manufacturer and model within canonical length limits;
- architecture `x86_64` or `arm64`;
- operating-system family `windows`, `macos`, or `ubuntu` plus a concrete version;
- a representable connection path;
- canonical observation outcome;
- valid observation timestamp;
- bounded condition and limitation strings;
- at most one driver entry, and when present both driver name and version;
- bounded firmware metadata.

The converter does not silently upgrade `unknown`, invent missing host details, or truncate semantic evidence into a stronger claim. Blockers remain visible to moderators and acceptance fails until the report can produce a canonical observation.

## Immutable accepted candidate

Acceptance writes one row to `private.community_observation_candidates`.

The candidate contains:

- deterministic observation ID `obs_community_<submission UUID without hyphens>`;
- the canonical `compatibility_observation` JSON candidate;
- SHA-256 of that candidate;
- SHA-256 of the original private community payload;
- reviewer and acceptance timestamp metadata kept in the private database.

The public observation contains no submitter ID. Its evidence type is always `community_report`, and its notes retain the source-payload hash for provenance without disclosing the contributor identity.

A rejected accepted candidate remains private and is excluded from the publication batch.

## Static publication gate

CompatForge's public compatibility product remains snapshot-based. Phase 6C therefore separates database acceptance from public publication.

For each accepted candidate:

1. An admin reads the accepted publication batch or the candidate JSON in `/moderation`.
2. The exact candidate is added to the reviewed static evidence input in a normal Git branch/PR.
3. Existing evidence validation, deterministic DuckDB/dbt snapshot checks, resolver tests, and web build gates run before merge.
4. The PR is merged to the canonical branch.
5. The admin records publication using the full 40-character merged commit SHA and the exact accepted candidate SHA-256.
6. PostgreSQL re-checks the candidate hash, stores the publication receipt, sets `published_observation_id`, and transitions the source submission from `accepted` to `published`.

If the candidate hash does not match, publication is refused. A database state change cannot substitute for the reviewed static-snapshot merge.

Phase 7 may automate more of this refresh workflow, but it must preserve the same acceptance/hash/merge/publication boundary.

## Audit trail

Every lifecycle transition remains append-only in `private.submission_state_events`. Phase 6C additionally records the moderator decision reason or publication receipt reason with the transition.

The moderator detail page exposes actor kind, previous state, next state, reason, and time, but not another user's account identity.

## Local verification

Run the clean-room database suite with:

```bash
supabase db start
supabase db lint --local --level error
supabase test db
```

Phase 6C tests verify least-privilege RPC structure, canonicalization blockers, deterministic observation construction, privacy boundaries, candidate hashing, admin-only publication, and transition-reason auditing.
