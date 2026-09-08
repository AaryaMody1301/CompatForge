# Community authentication setup

Phase 6B adds GitHub sign-in through Supabase Auth. The application uses GitHub only as the identity provider; authorization for community submissions is enforced by Supabase JWTs, Row Level Security, and the validated PostgreSQL RPC.

## 1. Create and migrate the hosted Supabase project

Create a Supabase project, then link the repository's local Supabase project and apply the committed migrations using the Supabase CLI.

The hosted database must contain both Phase 6 migrations before the community UI is enabled:

- `20260908000100_phase6a_community_submissions.sql`
- `20260908000200_phase6b_submission_controls.sql`

Do not put a service-role or Supabase secret key in the web application. Phase 6B requires only the public project URL and publishable key because authenticated writes use RPC validation and user-scoped access uses RLS.

## 2. Configure the GitHub OAuth App

Create a GitHub OAuth App for the hosted environment.

Use the live CompatForge URL as the OAuth App homepage. Set the GitHub OAuth App **Authorization callback URL** to the callback displayed by Supabase's GitHub provider configuration:

```text
https://<project-ref>.supabase.co/auth/v1/callback
```

For local Supabase CLI OAuth testing, the provider callback is:

```text
http://localhost:54321/auth/v1/callback
```

Add the resulting GitHub Client ID and Client Secret to **Supabase Dashboard -> Authentication -> Sign In / Providers -> GitHub**. The GitHub client secret belongs in Supabase, not in Vercel or browser JavaScript.

CompatForge does not request repository scopes or persist the GitHub provider access token. The provider establishes the Supabase user identity used by `auth.uid()`.

## 3. Configure Supabase redirect URLs

Set the Supabase Auth Site URL to the canonical production website.

Allow the application's PKCE callback route in **Authentication -> URL Configuration -> Redirect URLs**. For production, prefer the exact URL:

```text
https://<production-host>/auth/callback
```

For local development:

```text
http://localhost:3000/**
```

For Vercel previews, Supabase supports wildcard redirect patterns. Use the account/team-specific pattern documented by Supabase, for example:

```text
https://*-<team-or-account-slug>.vercel.app/**
```

Keep the production redirect exact even when preview wildcards are enabled.

## 4. Configure the Next.js deployment

Copy the two public values shown by the Supabase project into Vercel environment variables:

```text
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

The checked-in `apps/web/.env.example` documents the same names.

When either value is absent, public CompatForge pages continue to work and `/submissions` shows an explicit unconfigured state. This prevents an incomplete community-backend rollout from breaking the existing read-only compatibility product.

## 5. Acceptance check

After deploying the environment values and provider settings, verify this sequence on a preview deployment before production:

1. open `/submissions` while signed out;
2. choose **Sign in with GitHub**;
3. return through `/auth/callback` and confirm the signed-in submission dashboard renders;
4. open `/submissions/new`;
5. submit a synthetic/non-public test reproduction from an approved local handoff;
6. confirm it appears only in the signed-in user's queue;
7. confirm a different authenticated account cannot read the first user's row;
8. confirm repeated submissions hit the database-enforced rolling rate limit;
9. confirm equivalent fingerprints display only the opaque duplicate-candidate message;
10. remove/reject test rows through controlled administrative tooling before accepting real reports.

Phase 6B does not add moderator acceptance or publication actions. Those remain Phase 6C.
