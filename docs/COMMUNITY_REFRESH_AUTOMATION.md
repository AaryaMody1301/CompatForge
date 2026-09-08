# Accepted community refresh automation

Phase 7C automates preparation of review pull requests from immutable accepted community candidates. It does not automate moderation acceptance, merging, or Supabase publication receipts.

## Trust boundary

The Phase 6C sequence remains authoritative:

1. a reviewer accepts a submission;
2. PostgreSQL freezes one canonical `compatibility_observation` plus its SHA-256;
3. Phase 7C may prepare a Git branch and pull request containing that exact candidate;
4. normal repository CI and human review run;
5. the PR is merged to `main`;
6. an admin separately records the full merged commit SHA and the exact accepted candidate SHA-256 through `publish_community_submission`.

There is no database-to-`main` direct write and no automatic call to the publication RPC.

## Hash-exact repository materialization

Acceptance hashes the UTF-8 bytes of PostgreSQL's `jsonb::text` representation. The Phase 7C refresh RPC returns both the parsed `jsonb` candidate and that exact text representation.

`compatforge_pipeline.community_refresh` verifies that:

- SHA-256 of `observation_text` equals `observation_sha256`;
- parsing `observation_text` yields exactly the same JSON object as the RPC's `observation` value;
- the object satisfies the normal `compatibility_observation` contract;
- its observation ID, device ID, `community_report` source type, and repository source URL match the expected canonical path.

The tool then writes `observation_text` byte-for-byte to `data/evidence/observations/<observation_id>.json`. As a result, the committed file SHA-256 is the same hash frozen at acceptance. Reformatting or editing the file breaks verification.

Each automation PR also commits a manifest under `data/evidence/community-refresh/`. Normal CI verifies the manifest, candidate paths, file bytes, accepted SHA-256 values, observation contracts, and the explicit `automatic_publication: false` boundary.

## Least-privilege Supabase identity

Phase 7C adds `private.refresh_automation_memberships`. A dedicated automation user in Supabase Auth can be enrolled in this table without becoming a reviewer or admin:

```sql
insert into private.refresh_automation_memberships (user_id)
values ('<automation-auth-user-uuid>')
on conflict (user_id) do nothing;
```

That identity can call `get_community_refresh_batch()` but cannot use moderator review RPCs or the admin-only publication RPC because it has no `private.moderator_memberships` role.

An existing admin may also call the refresh batch RPC for manual verification.

Create a dedicated Auth user for automation and store only that user's login credentials in GitHub Actions secrets. Do not put a Supabase service-role/secret key into the workflow or web application.

## GitHub Actions configuration

The `.github/workflows/community-refresh.yml` workflow runs weekly and can also be dispatched manually. It is a no-op until all required secrets exist:

- `COMPATFORGE_SUPABASE_URL`;
- `COMPATFORGE_SUPABASE_PUBLISHABLE_KEY`;
- `COMPATFORGE_REFRESH_EMAIL`;
- `COMPATFORGE_REFRESH_PASSWORD`;
- `COMPATFORGE_REFRESH_GITHUB_TOKEN`.

`COMPATFORGE_REFRESH_GITHUB_TOKEN` must be a separate GitHub App installation token or fine-grained token able to push the bot-owned `automation/community-refresh` branch and create/update pull requests. The workflow's built-in `GITHUB_TOKEN` remains `contents: read` only.

A separate token is intentional: GitHub suppresses most workflow events caused by repository writes performed with `GITHUB_TOKEN`. Using a GitHub App or appropriately scoped token allows the automation-created pull request to trigger the normal `pull_request` CI path.

Recommended repository permissions for the refresh token are limited to:

- repository contents: write;
- pull requests: write;
- repository metadata: read.

It does not need Actions administration, secrets administration, or permission to approve its own pull request.

## Bot-owned branch behavior

The workflow force-updates only `automation/community-refresh` from the latest canonical branch and the current accepted/unpublished batch. Reviewers should not edit candidate files on this branch.

If a candidate needs a semantic correction, it no longer matches the immutable accepted hash and must go back through a new moderation decision rather than being hand-edited in the refresh PR.

If an accepted candidate is already present byte-for-byte on `main` but still lacks a Supabase publication receipt, the workflow creates no duplicate PR. It reports the candidate as already present so an admin can complete the existing Phase 6C receipt step.

## Local/offline preparation

The tool can also prepare a previously exported batch JSON without contacting Supabase:

```bash
python -m compatforge_pipeline.community_refresh prepare \
  --batch build/community-refresh/batch.json \
  --repository-root . \
  --base-commit <40-character-main-sha> \
  --prepared-at 2026-09-08T08:00:00Z \
  --result build/community-refresh/result.json
```

Verify a generated manifest with:

```bash
python -m compatforge_pipeline.community_refresh verify \
  --repository-root . \
  --manifest data/evidence/community-refresh/<batch-id>.json
```

This offline path is useful for development and incident recovery but does not weaken the same hash and contract checks.
