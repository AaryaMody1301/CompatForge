begin;

create extension if not exists pgtap with schema extensions;

select plan(9);

select ok(
  to_regclass('private.refresh_automation_memberships') is not null,
  'dedicated community refresh membership table exists'
);

select ok(
  not has_table_privilege(
    'authenticated',
    'private.refresh_automation_memberships',
    'SELECT'
  ),
  'authenticated users cannot directly read refresh automation membership'
);

select ok(
  has_function_privilege(
    'authenticated',
    'public.get_community_refresh_batch()',
    'EXECUTE'
  ),
  'authenticated sessions may invoke the refresh wrapper which performs its own authorization check'
);

select ok(
  not has_function_privilege(
    'anon',
    'public.get_community_refresh_batch()',
    'EXECUTE'
  ),
  'anonymous sessions cannot invoke the refresh batch RPC'
);

select ok(
  not (
    select p.prosecdef
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
      and p.proname = 'get_community_refresh_batch'
  ),
  'public refresh batch is a security-invoker wrapper'
);

select ok(
  (
    select p.prosecdef
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'private'
      and p.proname = 'get_community_refresh_batch_impl'
  ),
  'private refresh implementation is security definer'
);

select ok(
  pg_catalog.strpos(
    pg_get_functiondef('private.get_community_refresh_batch_impl()'::regprocedure),
    'candidate.observation::text'
  ) > 0,
  'refresh batch exposes the exact PostgreSQL jsonb text whose bytes were hashed at acceptance'
);

select ok(
  pg_catalog.strpos(
    pg_get_functiondef('private.get_community_refresh_batch_impl()'::regprocedure),
    $$submission.state = 'accepted'$$
  ) > 0
  and pg_catalog.strpos(
    pg_get_functiondef('private.get_community_refresh_batch_impl()'::regprocedure),
    'candidate.published_at is null'
  ) > 0,
  'refresh batch is limited to accepted and unpublished candidates'
);

select ok(
  pg_catalog.strpos(
    pg_get_functiondef('private.can_prepare_community_refresh()'::regprocedure),
    'refresh_automation_memberships'
  ) > 0
  and pg_catalog.strpos(
    pg_get_functiondef('private.can_prepare_community_refresh()'::regprocedure),
    $$get_current_moderator_role() = 'admin'$$
  ) > 0,
  'refresh access is restricted to dedicated automation identities or admins'
);

select * from finish();
rollback;
