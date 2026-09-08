begin;

create extension if not exists pgtap with schema extensions;

select plan(18);

select ok(
  to_regclass('public.evidence_submissions') is not null,
  'community submission table exists'
);

select ok(
  to_regclass('private.submission_moderation') is not null,
  'private moderation table exists'
);

select ok(
  to_regclass('private.submission_state_events') is not null,
  'private state event table exists'
);

select ok(
  (
    select relrowsecurity
    from pg_class
    where oid = 'public.evidence_submissions'::regclass
  ),
  'RLS is enabled on evidence_submissions'
);

select is(
  (
    select count(*)::integer
    from pg_policies
    where schemaname = 'public'
      and tablename = 'evidence_submissions'
  ),
  2,
  'exactly two read policies protect evidence_submissions'
);

select ok(
  has_table_privilege('authenticated', 'public.evidence_submissions', 'SELECT'),
  'authenticated users can select submissions allowed by RLS'
);

select ok(
  not has_table_privilege('authenticated', 'public.evidence_submissions', 'INSERT'),
  'authenticated users cannot bypass the validated submission RPC with direct inserts'
);

select ok(
  not has_table_privilege('authenticated', 'public.evidence_submissions', 'UPDATE'),
  'authenticated users cannot directly mutate moderation state'
);

select ok(
  not has_table_privilege('authenticated', 'public.evidence_submissions', 'DELETE'),
  'authenticated users cannot directly delete moderation records'
);

select ok(
  not has_table_privilege('anon', 'public.evidence_submissions', 'SELECT'),
  'anonymous users cannot read submissions'
);

select ok(
  has_function_privilege(
    'authenticated',
    'public.submit_community_evidence(jsonb)',
    'EXECUTE'
  ),
  'authenticated users can call the validated submission RPC'
);

select ok(
  not has_function_privilege('anon', 'public.submit_community_evidence(jsonb)', 'EXECUTE'),
  'anonymous users cannot call the submission RPC'
);

select ok(
  not has_table_privilege('authenticated', 'private.submission_moderation', 'SELECT'),
  'moderation details are not directly readable by authenticated users'
);

select ok(
  (
    select p.prosecdef
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'private'
      and p.proname = 'is_current_user_moderator'
  ),
  'moderator membership lookup is a security-definer function'
);

select ok(
  private.can_transition_submission_state('submitted', 'validated'),
  'submitted can transition to validated'
);

select ok(
  private.can_transition_submission_state('pending_review', 'accepted'),
  'pending review can transition to accepted'
);

select ok(
  private.can_transition_submission_state('accepted', 'published'),
  'accepted can transition to published'
);

select ok(
  not private.can_transition_submission_state('published', 'submitted'),
  'published is terminal and cannot transition back to submitted'
);

select * from finish();
rollback;
