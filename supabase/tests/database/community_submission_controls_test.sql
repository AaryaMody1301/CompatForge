begin;

create extension if not exists pgtap with schema extensions;

select plan(20);

select ok(
  private.community_array_has_duplicates('["same", "same"]'::jsonb),
  'community array contract detects duplicate scalar items'
);

select ok(
  private.community_array_has_duplicates('[{"name":"driver"}, {"name":"driver"}]'::jsonb),
  'community array contract detects duplicate object items'
);

select ok(
  not private.community_array_has_duplicates('["one", "two"]'::jsonb),
  'community array contract accepts unique items'
);

select ok(
  private.community_https_reference_valid('https://example.com/path?q=1')
    and private.community_https_reference_valid('https://[2001:db8::1]/path')
    and not private.community_https_reference_valid('https://%')
    and not private.community_https_reference_valid('https://bad host.example/path')
    and not private.community_https_reference_valid('https://example.com/%GG'),
  'community reference validator accepts valid HTTPS and rejects malformed authorities and escapes'
);

select ok(
  pg_catalog.strpos(
    pg_get_functiondef('private.validate_community_submission_insert()'::regprocedure),
    'interval ''5 minutes'''
  ) > 0
    and pg_catalog.strpos(
      pg_get_functiondef('private.validate_community_candidate_insert()'::regprocedure),
      'interval ''5 minutes'''
    ) > 0,
  'submission and candidate triggers share the web five-minute future-time tolerance'
);

select ok(
  pg_catalog.strpos(
    pg_get_functiondef('private.enforce_submission_rate_limit()'::regprocedure),
    'for update'
  ) > 0,
  'per-user row lock serializes concurrent rolling-window submission counts'
);

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
  not (
    select p.prosecdef
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'get_my_submission_dashboard'
  ),
  'public dashboard RPC is a security-invoker wrapper'
);

select ok(
  (
    select p.prosecdef
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'private'
      and p.proname = 'get_my_submission_dashboard_impl'
  ),
  'private dashboard implementation is security definer'
);

select ok(
  not (
    select p.prosecdef
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'submit_community_evidence'
  ),
  'public submission RPC is a security-invoker wrapper'
);

select ok(
  (
    select p.prosecdef
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'private'
      and p.proname = 'submit_community_evidence_impl'
  ),
  'private submission implementation is security definer'
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
    pg_get_functiondef('private.get_my_submission_dashboard_impl()'::regprocedure),
    'auth.uid()'
  ) > 0,
  'private dashboard implementation is scoped to the current authenticated user'
);

select ok(
  pg_catalog.strpos(
    pg_get_functiondef('private.submit_community_evidence_impl(jsonb)'::regprocedure),
    'pg_catalog.coalesce'
  ) = 0,
  'submission implementation does not schema-qualify the COALESCE expression'
);

select * from finish();
rollback;
