create extension if not exists pgcrypto with schema extensions;

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
grant usage on schema private to authenticated;

do $$
begin
  create type public.submission_state as enum (
    'submitted',
    'validated',
    'pending_review',
    'accepted',
    'published',
    'rejected'
  );
exception
  when duplicate_object then null;
end
$$;

create table public.evidence_submissions (
  id uuid primary key default gen_random_uuid(),
  submitter_id uuid not null references auth.users(id) on delete cascade,
  client_submission_id uuid not null,
  schema_version text not null default '1.0.0' check (schema_version = '1.0.0'),
  device_id text not null check (device_id ~ '^usb:[0-9A-F]{4}:[0-9A-F]{4}$'),
  observed_outcome text not null check (
    observed_outcome in ('works', 'works_with_conditions', 'fails')
  ),
  payload jsonb not null check (jsonb_typeof(payload) = 'object'),
  payload_sha256 text not null check (payload_sha256 ~ '^[0-9a-f]{64}$'),
  submission_fingerprint text not null check (
    submission_fingerprint ~ '^[0-9a-f]{64}$'
  ),
  state public.submission_state not null default 'submitted',
  published_observation_id text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint evidence_submissions_client_id_unique unique (submitter_id, client_submission_id),
  constraint evidence_submissions_payload_size check (octet_length(payload::text) <= 65536),
  constraint evidence_submissions_payload_record_type check (
    payload ->> 'record_type' = 'community_evidence_submission'
  ),
  constraint evidence_submissions_payload_schema check (
    payload ->> 'schema_version' = schema_version
  ),
  constraint evidence_submissions_payload_device check (
    payload ->> 'target_device_id' = device_id
  ),
  constraint evidence_submissions_payload_outcome check (
    payload #>> '{reproduction,outcome}' = observed_outcome
  ),
  constraint evidence_submissions_publication_link check (
    (state = 'published' and published_observation_id is not null)
    or (state <> 'published' and published_observation_id is null)
  )
);

comment on table public.evidence_submissions is
  'Private moderation queue for user-approved compatibility reproductions. Rows are not public evidence.';

create index evidence_submissions_submitter_created_idx
  on public.evidence_submissions (submitter_id, created_at desc);
create index evidence_submissions_state_created_idx
  on public.evidence_submissions (state, created_at);
create index evidence_submissions_device_state_idx
  on public.evidence_submissions (device_id, state);
create index evidence_submissions_fingerprint_idx
  on public.evidence_submissions (submission_fingerprint);

create table private.moderator_memberships (
  user_id uuid primary key references auth.users(id) on delete cascade,
  role text not null check (role in ('reviewer', 'admin')),
  created_at timestamptz not null default timezone('utc', now())
);

create table private.submission_moderation (
  submission_id uuid primary key references public.evidence_submissions(id) on delete cascade,
  reviewer_id uuid references auth.users(id) on delete set null,
  duplicate_of uuid references public.evidence_submissions(id) on delete set null,
  validation_errors jsonb not null default '[]'::jsonb check (
    jsonb_typeof(validation_errors) = 'array'
  ),
  risk_flags text[] not null default '{}'::text[],
  decision_reason text,
  updated_at timestamptz not null default timezone('utc', now()),
  constraint submission_moderation_not_self_duplicate check (duplicate_of is distinct from submission_id)
);

create table private.submission_state_events (
  id bigint generated always as identity primary key,
  submission_id uuid not null references public.evidence_submissions(id) on delete cascade,
  actor_user_id uuid references auth.users(id) on delete set null,
  actor_kind text not null check (actor_kind in ('submitter', 'moderator', 'system')),
  from_state public.submission_state,
  to_state public.submission_state not null,
  reason text,
  created_at timestamptz not null default timezone('utc', now())
);

create index submission_state_events_submission_idx
  on private.submission_state_events (submission_id, created_at);

create or replace function private.is_current_user_moderator()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from private.moderator_memberships membership
    where membership.user_id = auth.uid()
  );
$$;

revoke all on function private.is_current_user_moderator() from public;
grant execute on function private.is_current_user_moderator() to authenticated;

create or replace function private.can_transition_submission_state(
  from_state public.submission_state,
  to_state public.submission_state
)
returns boolean
language sql
immutable
set search_path = ''
as $$
  select case
    when from_state = to_state then true
    when from_state = 'submitted' and to_state in ('validated', 'rejected') then true
    when from_state = 'validated' and to_state in ('pending_review', 'rejected') then true
    when from_state = 'pending_review' and to_state in ('accepted', 'rejected') then true
    when from_state = 'accepted' and to_state in ('published', 'rejected') then true
    else false
  end;
$$;

revoke all on function private.can_transition_submission_state(
  public.submission_state,
  public.submission_state
) from public, anon, authenticated;

create or replace function private.guard_submission_transition()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.state is distinct from old.state
    and not private.can_transition_submission_state(old.state, new.state) then
    raise exception 'invalid submission state transition: % -> %', old.state, new.state;
  end if;

  new.updated_at := pg_catalog.timezone('utc', pg_catalog.now());
  return new;
end;
$$;

revoke all on function private.guard_submission_transition() from public, anon, authenticated;

create trigger evidence_submissions_guard_transition
before update on public.evidence_submissions
for each row execute function private.guard_submission_transition();

create or replace function private.record_submission_state_event()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  event_from_state public.submission_state;
  event_actor_kind text;
begin
  if tg_op = 'UPDATE' and new.state is not distinct from old.state then
    return new;
  end if;

  if tg_op = 'INSERT' then
    event_from_state := null;
  else
    event_from_state := old.state;
  end if;

  if auth.uid() is null then
    event_actor_kind := 'system';
  elsif private.is_current_user_moderator() then
    event_actor_kind := 'moderator';
  elsif auth.uid() = new.submitter_id then
    event_actor_kind := 'submitter';
  else
    event_actor_kind := 'system';
  end if;

  insert into private.submission_state_events (
    submission_id,
    actor_user_id,
    actor_kind,
    from_state,
    to_state
  ) values (
    new.id,
    auth.uid(),
    event_actor_kind,
    event_from_state,
    new.state
  );

  return new;
end;
$$;

revoke all on function private.record_submission_state_event() from public, anon, authenticated;

create trigger evidence_submissions_record_state
  after insert or update on public.evidence_submissions
  for each row execute function private.record_submission_state_event();

create or replace function public.submit_community_evidence(submission jsonb)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  request_user uuid := auth.uid();
  inserted_id uuid;
  semantic_payload jsonb;
  payload_hash text;
  fingerprint text;
begin
  if request_user is null then
    raise exception 'authentication required';
  end if;

  if pg_catalog.jsonb_typeof(submission) <> 'object' then
    raise exception 'submission must be a JSON object';
  end if;

  if pg_catalog.octet_length(submission::text) > 65536 then
    raise exception 'submission payload exceeds 64 KiB';
  end if;

  if submission ->> 'record_type' <> 'community_evidence_submission'
    or submission ->> 'schema_version' <> '1.0.0' then
    raise exception 'unsupported community submission contract';
  end if;

  if pg_catalog.coalesce((submission ->> 'evidence_ready')::boolean, true) then
    raise exception 'community submissions cannot be evidence-ready';
  end if;

  if submission ->> 'target_device_id' !~ '^usb:[0-9A-F]{4}:[0-9A-F]{4}$' then
    raise exception 'invalid target device identity';
  end if;

  if submission #>> '{reproduction,outcome}' not in (
    'works',
    'works_with_conditions',
    'fails'
  ) then
    raise exception 'invalid reproduction outcome';
  end if;

  if not pg_catalog.coalesce(
    (submission #>> '{handoff,user_approved_export}')::boolean,
    false
  ) then
    raise exception 'contribution handoff must be explicitly approved';
  end if;

  if not pg_catalog.coalesce(
    (submission #>> '{publication,anonymized_publication}')::boolean,
    false
  ) then
    raise exception 'initial community publication must be anonymized';
  end if;

  if pg_catalog.coalesce(
    (submission #>> '{privacy,contains_raw_diagnostic}')::boolean,
    true
  ) or pg_catalog.coalesce(
    (submission #>> '{privacy,contains_serial_numbers}')::boolean,
    true
  ) or pg_catalog.coalesce(
    (submission #>> '{privacy,contains_network_identifiers}')::boolean,
    true
  ) or pg_catalog.coalesce(
    (submission #>> '{privacy,contains_unrelated_usb_inventory}')::boolean,
    true
  ) or pg_catalog.coalesce(
    (submission #>> '{privacy,automatic_publication}')::boolean,
    true
  ) then
    raise exception 'submission violates the privacy/publication boundary';
  end if;

  semantic_payload := pg_catalog.jsonb_build_object(
    'target_device_id', submission -> 'target_device_id',
    'configuration', submission -> 'configuration',
    'reproduction', submission -> 'reproduction',
    'references', submission -> 'references'
  );

  payload_hash := pg_catalog.encode(
    extensions.digest(pg_catalog.convert_to(submission::text, 'UTF8'), 'sha256'),
    'hex'
  );
  fingerprint := pg_catalog.encode(
    extensions.digest(pg_catalog.convert_to(semantic_payload::text, 'UTF8'), 'sha256'),
    'hex'
  );

  insert into public.evidence_submissions (
    submitter_id,
    client_submission_id,
    schema_version,
    device_id,
    observed_outcome,
    payload,
    payload_sha256,
    submission_fingerprint
  ) values (
    request_user,
    (submission ->> 'client_submission_id')::uuid,
    '1.0.0',
    submission ->> 'target_device_id',
    submission #>> '{reproduction,outcome}',
    submission,
    payload_hash,
    fingerprint
  )
  returning id into inserted_id;

  return inserted_id;
end;
$$;

revoke all on function public.submit_community_evidence(jsonb) from public, anon;
grant execute on function public.submit_community_evidence(jsonb) to authenticated;

alter table public.evidence_submissions enable row level security;

revoke all on table public.evidence_submissions from anon, authenticated;
grant select on table public.evidence_submissions to authenticated;

create policy "submitters can read own submissions"
on public.evidence_submissions
for select
to authenticated
using ((select auth.uid()) = submitter_id);

create policy "moderators can read all submissions"
on public.evidence_submissions
for select
to authenticated
using (private.is_current_user_moderator());

revoke all on table private.moderator_memberships from public, anon, authenticated;
revoke all on table private.submission_moderation from public, anon, authenticated;
revoke all on table private.submission_state_events from public, anon, authenticated;
