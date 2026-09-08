-- Phase 6A shipped the submission RPC with COALESCE schema-qualified as if it
-- were a normal function. PostgreSQL implements COALESCE as a special SQL
-- expression, so Phase 6B replaces the function before the hosted API is used.
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

  if coalesce((submission ->> 'evidence_ready')::boolean, true) then
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

  if not coalesce(
    (submission #>> '{handoff,user_approved_export}')::boolean,
    false
  ) then
    raise exception 'contribution handoff must be explicitly approved';
  end if;

  if not coalesce(
    (submission #>> '{publication,anonymized_publication}')::boolean,
    false
  ) then
    raise exception 'initial community publication must be anonymized';
  end if;

  if coalesce(
    (submission #>> '{privacy,contains_raw_diagnostic}')::boolean,
    true
  ) or coalesce(
    (submission #>> '{privacy,contains_serial_numbers}')::boolean,
    true
  ) or coalesce(
    (submission #>> '{privacy,contains_network_identifiers}')::boolean,
    true
  ) or coalesce(
    (submission #>> '{privacy,contains_unrelated_usb_inventory}')::boolean,
    true
  ) or coalesce(
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

create or replace function private.enforce_submission_rate_limit()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  hourly_count integer;
  daily_count integer;
begin
  select
    count(*) filter (
      where submission.created_at >= pg_catalog.now() - interval '1 hour'
    )::integer,
    count(*)::integer
  into hourly_count, daily_count
  from public.evidence_submissions submission
  where submission.submitter_id = new.submitter_id
    and submission.created_at >= pg_catalog.now() - interval '24 hours';

  if hourly_count >= 5 then
    raise exception 'submission rate limit exceeded: 5 per hour';
  end if;

  if daily_count >= 20 then
    raise exception 'submission rate limit exceeded: 20 per 24 hours';
  end if;

  return new;
end;
$$;

revoke all on function private.enforce_submission_rate_limit() from public, anon, authenticated;

create trigger evidence_submissions_rate_limit
before insert on public.evidence_submissions
for each row execute function private.enforce_submission_rate_limit();

create or replace function private.flag_submission_duplicate_candidate()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  duplicate_exists boolean;
begin
  select exists (
    select 1
    from public.evidence_submissions candidate
    where candidate.submission_fingerprint = new.submission_fingerprint
      and candidate.id <> new.id
      and candidate.state <> 'rejected'
  ) into duplicate_exists;

  if duplicate_exists then
    insert into private.submission_moderation (
      submission_id,
      risk_flags
    ) values (
      new.id,
      array['duplicate_candidate']::text[]
    )
    on conflict (submission_id) do update
    set risk_flags = case
      when 'duplicate_candidate' = any(private.submission_moderation.risk_flags)
        then private.submission_moderation.risk_flags
      else pg_catalog.array_append(
        private.submission_moderation.risk_flags,
        'duplicate_candidate'
      )
    end,
    updated_at = pg_catalog.timezone('utc', pg_catalog.now());
  end if;

  return new;
end;
$$;

revoke all on function private.flag_submission_duplicate_candidate() from public, anon, authenticated;

create trigger evidence_submissions_flag_duplicate
  after insert on public.evidence_submissions
  for each row execute function private.flag_submission_duplicate_candidate();

create or replace function public.get_my_submission_dashboard()
returns table (
  id uuid,
  client_submission_id uuid,
  device_id text,
  observed_outcome text,
  state public.submission_state,
  created_at timestamptz,
  updated_at timestamptz,
  duplicate_candidate boolean
)
language sql
stable
security definer
set search_path = ''
as $$
  select
    submission.id,
    submission.client_submission_id,
    submission.device_id,
    submission.observed_outcome,
    submission.state,
    submission.created_at,
    submission.updated_at,
    exists (
      select 1
      from public.evidence_submissions candidate
      where candidate.submission_fingerprint = submission.submission_fingerprint
        and candidate.id <> submission.id
        and candidate.state <> 'rejected'
    ) as duplicate_candidate
  from public.evidence_submissions submission
  where submission.submitter_id = auth.uid()
  order by submission.created_at desc
  limit 100;
$$;

revoke all on function public.get_my_submission_dashboard() from public, anon;
grant execute on function public.get_my_submission_dashboard() to authenticated;

comment on function public.get_my_submission_dashboard() is
  'Returns only the current user''s submission status plus an opaque duplicate-candidate flag.';
