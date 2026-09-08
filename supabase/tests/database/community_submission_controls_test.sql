begin;

create extension if not exists pgtap with schema extensions;

select plan(11);

select ok(
  exists (
    select 1
    from pg_trigger
    where tgrelid = 'public.evidence_submissions'::regclass
      and tgname = 'evidence_submissions_rate_limit'
      and not tgisinternal
  ),
  'database-enforced submission rate-limit trigger exists'
);

select ok(
  exists (
    select 1
    from pg_trigger
    where tgrelid = 'public.evidence_submissions'::regclass
      and tgname = 'evidence_submissions_flag_duplicate'
      and not tgisinternal
  ),
  'duplicate-candidate moderation trigger exists'
);

select ok(
  (
    select p.prosecdef
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'private'
      and p.proname = 'enforce_submission_rate_limit'
  ),
  'rate-limit trigger function is security definer'
);

select ok(
  (
    select p.prosecdef
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'private'
      and p.proname = 'flag_submission_duplicate_candidate'
  ),
  'duplicate-candidate trigger function is security definer'
);

select ok(
  (
    select p.prosecdef
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'get_my_submission_dashboard'
  ),
  'submission dashboard function is security definer'
);

select ok(
  has_function_privilege(
    'authenticated',
    'public.get_my_submission_dashboard()',
    'EXECUTE'
  ),
  'authenticated users can read their dashboard through the bounded RPC'
);

select ok(
  not has_function_privilege(
    'anon',
    'public.get_my_submission_dashboard()',
    'EXECUTE'
  ),
  'anonymous users cannot call the submission dashboard RPC'
);

select ok(
  pg_catalog.strpos(
    pg_get_functiondef('private.enforce_submission_rate_limit()'::regprocedure),
    '5 per hour'
  ) > 0,
  'hourly rate-limit threshold is encoded in the database function'
);

select ok(
  pg_catalog.strpos(
    pg_get_functiondef('private.enforce_submission_rate_limit()'::regprocedure),
    '20 per 24 hours'
  ) > 0,
  'daily rate-limit threshold is encoded in the database function'
);

select ok(
  pg_catalog.strpos(
    pg_get_functiondef('public.get_my_submission_dashboard()'::regprocedure),
    'auth.uid()'
  ) > 0,
  'dashboard is scoped to the current authenticated user'
);

select ok(
  pg_catalog.strpos(
    pg_get_functiondef('public.submit_community_evidence(jsonb)'::regprocedure),
    'pg_catalog.coalesce'
  ) = 0,
  'submission RPC does not schema-qualify the COALESCE expression'
);

select * from finish();
rollback;
