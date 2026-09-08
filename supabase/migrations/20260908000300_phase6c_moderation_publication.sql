-- Phase 6C: bounded moderator review, deterministic canonicalization, and
-- publication receipts. Public compatibility serving remains snapshot-based.

-- Moderators now use bounded RPCs instead of broad direct RLS reads. This keeps
-- submitter identity out of the normal moderation product surface.
drop policy if exists "moderators can read all submissions" on public.evidence_submissions;

create table private.community_observation_candidates (
  submission_id uuid primary key references public.evidence_submissions(id) on delete restrict,
  observation_id text not null unique check (
    observation_id ~ '^obs_[a-z0-9][a-z0-9_-]{5,63}$'
  ),
  device_id text not null check (device_id ~ '^usb:[0-9A-F]{4}:[0-9A-F]{4}$'),
  observation jsonb not null check (pg_catalog.jsonb_typeof(observation) = 'object'),
  observation_sha256 text not null check (observation_sha256 ~ '^[0-9a-f]{64}$'),
  source_payload_sha256 text not null check (source_payload_sha256 ~ '^[0-9a-f]{64}$'),
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default pg_catalog.now(),
  published_at timestamptz,
  published_by uuid references auth.users(id) on delete restrict,
  snapshot_commit_sha text check (snapshot_commit_sha ~ '^[0-9a-f]{40}$'),
  constraint community_candidate_observation_identity check (
    observation ->> 'observation_id' = observation_id
    and observation ->> 'device_id' = device_id
    and observation ->> 'record_type' = 'compatibility_observation'
    and observation #>> '{evidence,source_type}' = 'community_report'
  ),
  constraint community_candidate_publication_fields check (
    (
      published_at is null
      and published_by is null
      and snapshot_commit_sha is null
    )
    or (
      published_at is not null
      and published_by is not null
      and snapshot_commit_sha is not null
    )
  )
);

create index community_observation_candidates_created_idx
  on private.community_observation_candidates (created_at desc);
create index community_observation_candidates_published_idx
  on private.community_observation_candidates (published_at, created_at);

comment on table private.community_observation_candidates is
  'Immutable reviewed compatibility_observation candidates. Accepted candidates are not public evidence until an admin records the merged snapshot commit and transitions the source submission to published.';

revoke all on table private.community_observation_candidates from public, anon, authenticated;

create or replace function private.get_current_moderator_role()
returns text
language sql
stable
security definer
set search_path = ''
as $$
  select membership.role
  from private.moderator_memberships membership
  where membership.user_id = auth.uid();
$$;

revoke all on function private.get_current_moderator_role() from public, anon;
grant execute on function private.get_current_moderator_role() to authenticated;

-- Keep privileged submission writes outside the API-exposed public schema.
create or replace function private.submit_community_evidence_impl(submission jsonb)
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

  if pg_catalog.jsonb_typeof(submission) is distinct from 'object' then
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

revoke all on function private.submit_community_evidence_impl(jsonb) from public, anon;
grant execute on function private.submit_community_evidence_impl(jsonb) to authenticated;

create or replace function public.submit_community_evidence(submission jsonb)
returns uuid
language sql
security invoker
set search_path = ''
as $$
  select private.submit_community_evidence_impl(submission);
$$;

revoke all on function public.submit_community_evidence(jsonb) from public, anon;
grant execute on function public.submit_community_evidence(jsonb) to authenticated;

create or replace function private.get_my_submission_dashboard_impl()
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

revoke all on function private.get_my_submission_dashboard_impl() from public, anon;
grant execute on function private.get_my_submission_dashboard_impl() to authenticated;

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
security invoker
set search_path = ''
as $$
  select * from private.get_my_submission_dashboard_impl();
$$;

revoke all on function public.get_my_submission_dashboard() from public, anon;
grant execute on function public.get_my_submission_dashboard() to authenticated;

-- Canonicalization is intentionally stricter than submission acceptance. A
-- community report can be valid for review while still lacking enough concrete
-- configuration detail to become a compatibility_observation.
create or replace function private.community_canonicalization_errors(submission jsonb)
returns jsonb
language plpgsql
stable
set search_path = ''
as $$
declare
  errors jsonb := '[]'::jsonb;
  host_manufacturer text := nullif(pg_catalog.btrim(coalesce(submission #>> '{configuration,host,manufacturer}', '')), '');
  host_model text := nullif(pg_catalog.btrim(coalesce(submission #>> '{configuration,host,model}', '')), '');
  os_family text := submission #>> '{configuration,operating_system,family}';
  os_version text := submission #>> '{configuration,operating_system,version}';
  os_build text := submission #>> '{configuration,operating_system,build}';
  architecture text := submission #>> '{configuration,architecture}';
  connection_kind text := submission #>> '{configuration,connection_path}';
  outcome text := submission #>> '{reproduction,outcome}';
  observed_at_text text := submission #>> '{reproduction,observed_at}';
  conditions jsonb := submission #> '{reproduction,conditions}';
  limitations jsonb := submission #> '{reproduction,limitations}';
  drivers jsonb := submission #> '{configuration,drivers}';
  driver jsonb;
  firmware_version text := submission #>> '{reproduction,firmware_version}';
begin
  if pg_catalog.jsonb_typeof(submission) is distinct from 'object' then
    return pg_catalog.jsonb_build_array('submission payload must be an object');
  end if;

  if pg_catalog.jsonb_typeof(submission #> '{configuration,host,manufacturer}') is distinct from 'string'
    or host_manufacturer is null then
    errors := errors || pg_catalog.jsonb_build_array('host manufacturer is required for canonical publication');
  elsif pg_catalog.char_length(host_manufacturer) > 120 then
    errors := errors || pg_catalog.jsonb_build_array('host manufacturer exceeds the canonical 120 character limit');
  end if;

  if pg_catalog.jsonb_typeof(submission #> '{configuration,host,model}') is distinct from 'string'
    or host_model is null then
    errors := errors || pg_catalog.jsonb_build_array('host model is required for canonical publication');
  elsif pg_catalog.char_length(host_model) > 160 then
    errors := errors || pg_catalog.jsonb_build_array('host model exceeds the canonical 160 character limit');
  end if;

  if pg_catalog.jsonb_typeof(submission #> '{configuration,architecture}') is distinct from 'string'
    or architecture not in ('x86_64', 'arm64') then
    errors := errors || pg_catalog.jsonb_build_array('architecture must be x86_64 or arm64 for canonical publication');
  end if;

  if pg_catalog.jsonb_typeof(submission #> '{configuration,operating_system,family}') is distinct from 'string'
    or os_family not in ('windows', 'macos', 'ubuntu') then
    errors := errors || pg_catalog.jsonb_build_array('operating system family must be windows, macos, or ubuntu for canonical publication');
  end if;

  if pg_catalog.jsonb_typeof(submission #> '{configuration,operating_system,version}') is distinct from 'string'
    or os_version is null or pg_catalog.btrim(os_version) = '' then
    errors := errors || pg_catalog.jsonb_build_array('operating system version is required for canonical publication');
  elsif pg_catalog.char_length(os_version) > 80 then
    errors := errors || pg_catalog.jsonb_build_array('operating system version exceeds the canonical 80 character limit');
  end if;

  if submission #> '{configuration,operating_system,build}' is not null then
    if pg_catalog.jsonb_typeof(submission #> '{configuration,operating_system,build}') is distinct from 'string' then
      errors := errors || pg_catalog.jsonb_build_array('operating system build must be a string when present');
    elsif pg_catalog.char_length(os_build) > 80 then
      errors := errors || pg_catalog.jsonb_build_array('operating system build exceeds the canonical 80 character limit');
    end if;
  end if;

  if pg_catalog.jsonb_typeof(submission #> '{configuration,connection_path}') is distinct from 'string'
    or connection_kind not in ('direct_port', 'usb_hub', 'unspecified') then
    errors := errors || pg_catalog.jsonb_build_array('connection path is not representable by the canonical observation contract');
  end if;

  if pg_catalog.jsonb_typeof(submission #> '{reproduction,outcome}') is distinct from 'string'
    or outcome not in ('works', 'works_with_conditions', 'fails') then
    errors := errors || pg_catalog.jsonb_build_array('outcome is not a canonical observation outcome');
  end if;

  if pg_catalog.jsonb_typeof(submission #> '{reproduction,observed_at}') is distinct from 'string'
    or observed_at_text is null then
    errors := errors || pg_catalog.jsonb_build_array('observation timestamp is required');
  else
    begin
      perform observed_at_text::timestamptz;
    exception
      when others then
        errors := errors || pg_catalog.jsonb_build_array('observation timestamp is not a valid timestamp');
    end;
  end if;

  if pg_catalog.jsonb_typeof(conditions) is distinct from 'array' then
    errors := errors || pg_catalog.jsonb_build_array('conditions must be an array');
  else
    if outcome = 'works_with_conditions' and pg_catalog.jsonb_array_length(conditions) = 0 then
      errors := errors || pg_catalog.jsonb_build_array('conditional outcomes require at least one condition');
    end if;
    if exists (
      select 1
      from pg_catalog.jsonb_array_elements(conditions) as condition(value)
      where pg_catalog.jsonb_typeof(condition.value) is distinct from 'string'
        or pg_catalog.char_length(condition.value #>> '{}') > 500
    ) then
      errors := errors || pg_catalog.jsonb_build_array('conditions must be strings of at most 500 characters');
    end if;
  end if;

  if pg_catalog.jsonb_typeof(limitations) is distinct from 'array' then
    errors := errors || pg_catalog.jsonb_build_array('limitations must be an array');
  else
    if pg_catalog.jsonb_array_length(limitations) = 0 then
      errors := errors || pg_catalog.jsonb_build_array('at least one limitation is required for canonical publication');
    end if;
    if exists (
      select 1
      from pg_catalog.jsonb_array_elements(limitations) as limitation(value)
      where pg_catalog.jsonb_typeof(limitation.value) is distinct from 'string'
        or pg_catalog.char_length(limitation.value #>> '{}') > 500
    ) then
      errors := errors || pg_catalog.jsonb_build_array('limitations must be strings of at most 500 characters');
    end if;
  end if;

  if pg_catalog.jsonb_typeof(drivers) is distinct from 'array' then
    errors := errors || pg_catalog.jsonb_build_array('drivers must be an array');
  elsif pg_catalog.jsonb_array_length(drivers) > 1 then
    errors := errors || pg_catalog.jsonb_build_array('canonical publication currently supports at most one driver record');
  elsif pg_catalog.jsonb_array_length(drivers) = 1 then
    driver := drivers -> 0;
    if pg_catalog.jsonb_typeof(driver) is distinct from 'object'
      or pg_catalog.jsonb_typeof(driver -> 'name') is distinct from 'string'
      or pg_catalog.jsonb_typeof(driver -> 'version') is distinct from 'string'
      or nullif(pg_catalog.btrim(coalesce(driver ->> 'name', '')), '') is null
      or nullif(pg_catalog.btrim(coalesce(driver ->> 'version', '')), '') is null then
      errors := errors || pg_catalog.jsonb_build_array('a submitted driver must include both string name and version fields for canonical publication');
    elsif pg_catalog.char_length(driver ->> 'name') > 160
      or pg_catalog.char_length(driver ->> 'version') > 80 then
      errors := errors || pg_catalog.jsonb_build_array('submitted driver metadata exceeds canonical length limits');
    end if;
  end if;

  if submission #> '{reproduction,firmware_version}' is not null then
    if pg_catalog.jsonb_typeof(submission #> '{reproduction,firmware_version}') is distinct from 'string' then
      errors := errors || pg_catalog.jsonb_build_array('firmware version must be a string when present');
    elsif pg_catalog.char_length(firmware_version) > 80 then
      errors := errors || pg_catalog.jsonb_build_array('firmware version exceeds the canonical 80 character limit');
    end if;
  end if;

  return errors;
end;
$$;

revoke all on function private.community_canonicalization_errors(jsonb) from public, anon, authenticated;

create or replace function private.build_community_observation(
  submission_id uuid,
  submission jsonb,
  source_payload_sha256 text,
  recorded_at timestamptz
)
returns jsonb
language plpgsql
stable
set search_path = ''
as $$
declare
  observation_id text := 'obs_community_' || pg_catalog.replace(submission_id::text, '-', '');
  conditions jsonb := submission #> '{reproduction,conditions}';
  limitations jsonb := submission #> '{reproduction,limitations}';
  drivers jsonb := submission #> '{configuration,drivers}';
  driver jsonb;
  source_excerpt text := pg_catalog.left(submission #>> '{reproduction,steps_summary}', 1000);
  note_text text := 'Reviewed community reproduction. Source payload SHA-256: ' || source_payload_sha256 || '.';
  observation jsonb;
begin
  if nullif(submission #>> '{reproduction,software_version}', '') is not null then
    note_text := note_text || ' Reported software version: ' || (submission #>> '{reproduction,software_version}') || '.';
  end if;

  if pg_catalog.jsonb_array_length(drivers) = 1
    and nullif(drivers -> 0 ->> 'provider', '') is not null then
    note_text := note_text || ' Reported driver provider: ' || (drivers -> 0 ->> 'provider') || '.';
  end if;

  observation := pg_catalog.jsonb_build_object(
    'schema_version', '1.0.0',
    'record_type', 'compatibility_observation',
    'observation_id', observation_id,
    'device_id', submission ->> 'target_device_id',
    'host', pg_catalog.jsonb_strip_nulls(pg_catalog.jsonb_build_object(
      'manufacturer', submission #>> '{configuration,host,manufacturer}',
      'model', submission #>> '{configuration,host,model}',
      'architecture', submission #>> '{configuration,architecture}',
      'operating_system', pg_catalog.jsonb_strip_nulls(pg_catalog.jsonb_build_object(
        'family', submission #>> '{configuration,operating_system,family}',
        'version', submission #>> '{configuration,operating_system,version}',
        'build', submission #>> '{configuration,operating_system,build}'
      ))
    )),
    'connection_path', pg_catalog.jsonb_build_array(pg_catalog.jsonb_build_object(
      'kind', submission #>> '{configuration,connection_path}'
    )),
    'outcome', submission #>> '{reproduction,outcome}',
    'evidence', pg_catalog.jsonb_build_object(
      'source_type', 'community_report',
      'source_url', 'https://compatforge.dev/evidence/' || observation_id,
      'source_title', 'CompatForge reviewed community reproduction ' || observation_id,
      'source_excerpt', source_excerpt
    ),
    'observed_at', pg_catalog.to_char(
      (submission #>> '{reproduction,observed_at}')::timestamptz at time zone 'UTC',
      'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'
    ),
    'recorded_at', pg_catalog.to_char(
      recorded_at at time zone 'UTC',
      'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'
    ),
    'limitations', limitations,
    'notes', note_text
  );

  if pg_catalog.jsonb_array_length(conditions) > 0 then
    observation := observation || pg_catalog.jsonb_build_object('conditions', conditions);
  end if;

  if pg_catalog.jsonb_array_length(drivers) = 1 then
    driver := drivers -> 0;
    observation := observation || pg_catalog.jsonb_build_object(
      'driver', pg_catalog.jsonb_build_object(
        'name', driver ->> 'name',
        'version', driver ->> 'version'
      )
    );
  end if;

  if nullif(submission #>> '{reproduction,firmware_version}', '') is not null then
    observation := observation || pg_catalog.jsonb_build_object(
      'firmware_version', submission #>> '{reproduction,firmware_version}'
    );
  end if;

  return observation;
end;
$$;

revoke all on function private.build_community_observation(uuid, jsonb, text, timestamptz)
  from public, anon, authenticated;

-- State event reasons are supplied by the only RPCs allowed to mutate review
-- state. A transaction-local custom setting avoids any cross-request state.
create or replace function private.record_submission_state_event()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  event_from_state public.submission_state;
  event_actor_kind text;
  event_reason text := nullif(
    pg_catalog.current_setting('compatforge.transition_reason', true),
    ''
  );
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
    to_state,
    reason
  ) values (
    new.id,
    auth.uid(),
    event_actor_kind,
    event_from_state,
    new.state,
    event_reason
  );

  return new;
end;
$$;

revoke all on function private.record_submission_state_event() from public, anon, authenticated;

create or replace function private.get_moderation_queue_impl()
returns table (
  submission_id uuid,
  device_id text,
  observed_outcome text,
  state public.submission_state,
  created_at timestamptz,
  updated_at timestamptz,
  validation_error_count integer,
  risk_flags text[],
  duplicate_candidate boolean,
  candidate_observation_id text,
  candidate_sha256 text
)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
  if auth.uid() is null or private.get_current_moderator_role() is null then
    raise exception 'moderator authorization required';
  end if;

  return query
  select
    submission.id,
    submission.device_id,
    submission.observed_outcome,
    submission.state,
    submission.created_at,
    submission.updated_at,
    coalesce(pg_catalog.jsonb_array_length(moderation.validation_errors), 0)::integer,
    coalesce(moderation.risk_flags, '{}'::text[]),
    'duplicate_candidate' = any(coalesce(moderation.risk_flags, '{}'::text[])),
    candidate.observation_id,
    candidate.observation_sha256
  from public.evidence_submissions submission
  left join private.submission_moderation moderation
    on moderation.submission_id = submission.id
  left join private.community_observation_candidates candidate
    on candidate.submission_id = submission.id
  order by
    case submission.state
      when 'pending_review' then 1
      when 'validated' then 2
      when 'submitted' then 3
      when 'accepted' then 4
      when 'published' then 5
      when 'rejected' then 6
    end,
    submission.created_at asc
  limit 200;
end;
$$;

revoke all on function private.get_moderation_queue_impl() from public, anon;
grant execute on function private.get_moderation_queue_impl() to authenticated;

create or replace function public.get_moderation_queue()
returns table (
  submission_id uuid,
  device_id text,
  observed_outcome text,
  state public.submission_state,
  created_at timestamptz,
  updated_at timestamptz,
  validation_error_count integer,
  risk_flags text[],
  duplicate_candidate boolean,
  candidate_observation_id text,
  candidate_sha256 text
)
language sql
stable
security invoker
set search_path = ''
as $$
  select * from private.get_moderation_queue_impl();
$$;

revoke all on function public.get_moderation_queue() from public, anon;
grant execute on function public.get_moderation_queue() to authenticated;

create or replace function private.get_moderation_submission_impl(requested_submission_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  result jsonb;
begin
  if auth.uid() is null or private.get_current_moderator_role() is null then
    raise exception 'moderator authorization required';
  end if;

  select pg_catalog.jsonb_build_object(
    'submission', pg_catalog.jsonb_build_object(
      'id', submission.id,
      'device_id', submission.device_id,
      'observed_outcome', submission.observed_outcome,
      'state', submission.state,
      'payload', submission.payload,
      'payload_sha256', submission.payload_sha256,
      'submission_fingerprint', submission.submission_fingerprint,
      'published_observation_id', submission.published_observation_id,
      'created_at', submission.created_at,
      'updated_at', submission.updated_at
    ),
    'moderation', pg_catalog.jsonb_build_object(
      'validation_errors', coalesce(moderation.validation_errors, '[]'::jsonb),
      'risk_flags', coalesce(pg_catalog.to_jsonb(moderation.risk_flags), '[]'::jsonb),
      'decision_reason', moderation.decision_reason,
      'reviewer_assigned', moderation.reviewer_id is not null,
      'updated_at', moderation.updated_at
    ),
    'candidate', case
      when candidate.submission_id is null then null
      else pg_catalog.jsonb_build_object(
        'observation_id', candidate.observation_id,
        'observation', candidate.observation,
        'observation_sha256', candidate.observation_sha256,
        'source_payload_sha256', candidate.source_payload_sha256,
        'created_at', candidate.created_at,
        'published_at', candidate.published_at,
        'snapshot_commit_sha', candidate.snapshot_commit_sha
      )
    end,
    'events', coalesce((
      select pg_catalog.jsonb_agg(
        pg_catalog.jsonb_build_object(
          'actor_kind', event.actor_kind,
          'from_state', event.from_state,
          'to_state', event.to_state,
          'reason', event.reason,
          'created_at', event.created_at
        ) order by event.id
      )
      from private.submission_state_events event
      where event.submission_id = submission.id
    ), '[]'::jsonb)
  )
  into result
  from public.evidence_submissions submission
  left join private.submission_moderation moderation
    on moderation.submission_id = submission.id
  left join private.community_observation_candidates candidate
    on candidate.submission_id = submission.id
  where submission.id = requested_submission_id;

  return result;
end;
$$;

revoke all on function private.get_moderation_submission_impl(uuid) from public, anon;
grant execute on function private.get_moderation_submission_impl(uuid) to authenticated;

create or replace function public.get_moderation_submission(submission_id uuid)
returns jsonb
language sql
stable
security invoker
set search_path = ''
as $$
  select private.get_moderation_submission_impl(submission_id);
$$;

revoke all on function public.get_moderation_submission(uuid) from public, anon;
grant execute on function public.get_moderation_submission(uuid) to authenticated;

create or replace function private.review_community_submission_impl(
  requested_submission_id uuid,
  review_action text,
  decision_reason text default null
)
returns public.submission_state
language plpgsql
security definer
set search_path = ''
as $$
declare
  request_user uuid := auth.uid();
  moderator_role text := private.get_current_moderator_role();
  submission public.evidence_submissions%rowtype;
  blockers jsonb;
  reason text := nullif(pg_catalog.btrim(coalesce(decision_reason, '')), '');
  accepted_at timestamptz;
  candidate jsonb;
  candidate_sha text;
begin
  if request_user is null or moderator_role is null then
    raise exception 'moderator authorization required';
  end if;

  if reason is not null and pg_catalog.char_length(reason) > 1000 then
    raise exception 'decision reason exceeds 1000 characters';
  end if;

  select *
  into submission
  from public.evidence_submissions source
  where source.id = requested_submission_id
  for update;

  if not found then
    raise exception 'submission not found';
  end if;

  if review_action = 'validate' then
    if submission.state <> 'submitted' then
      raise exception 'validate requires submitted state';
    end if;

    blockers := private.community_canonicalization_errors(submission.payload);
    insert into private.submission_moderation (
      submission_id,
      reviewer_id,
      validation_errors,
      updated_at
    ) values (
      submission.id,
      request_user,
      blockers,
      pg_catalog.now()
    )
    on conflict (submission_id) do update
    set reviewer_id = excluded.reviewer_id,
        validation_errors = excluded.validation_errors,
        updated_at = excluded.updated_at;

    perform pg_catalog.set_config(
      'compatforge.transition_reason',
      coalesce(reason, 'Submission contract reviewed; canonical publication blockers recorded.'),
      true
    );
    update public.evidence_submissions set state = 'validated' where id = submission.id;
    return 'validated';
  end if;

  if review_action = 'queue_review' then
    if submission.state <> 'validated' then
      raise exception 'queue_review requires validated state';
    end if;

    insert into private.submission_moderation (submission_id, reviewer_id, updated_at)
    values (submission.id, request_user, pg_catalog.now())
    on conflict (submission_id) do update
    set reviewer_id = excluded.reviewer_id,
        updated_at = excluded.updated_at;

    perform pg_catalog.set_config(
      'compatforge.transition_reason',
      coalesce(reason, 'Submission moved to human review.'),
      true
    );
    update public.evidence_submissions set state = 'pending_review' where id = submission.id;
    return 'pending_review';
  end if;

  if review_action = 'reject' then
    if submission.state not in ('submitted', 'validated', 'pending_review', 'accepted') then
      raise exception 'submission cannot be rejected from state %', submission.state;
    end if;
    if reason is null or pg_catalog.char_length(reason) < 10 then
      raise exception 'rejection requires a decision reason of at least 10 characters';
    end if;

    insert into private.submission_moderation (
      submission_id,
      reviewer_id,
      decision_reason,
      updated_at
    ) values (
      submission.id,
      request_user,
      reason,
      pg_catalog.now()
    )
    on conflict (submission_id) do update
    set reviewer_id = excluded.reviewer_id,
        decision_reason = excluded.decision_reason,
        updated_at = excluded.updated_at;

    perform pg_catalog.set_config('compatforge.transition_reason', reason, true);
    update public.evidence_submissions set state = 'rejected' where id = submission.id;
    return 'rejected';
  end if;

  if review_action = 'accept' then
    if submission.state <> 'pending_review' then
      raise exception 'accept requires pending_review state';
    end if;
    if reason is null or pg_catalog.char_length(reason) < 10 then
      raise exception 'acceptance requires a decision reason of at least 10 characters';
    end if;

    blockers := private.community_canonicalization_errors(submission.payload);
    if pg_catalog.jsonb_array_length(blockers) > 0 then
      raise exception 'submission has canonicalization blockers: %', blockers::text;
    end if;

    accepted_at := pg_catalog.now();
    candidate := private.build_community_observation(
      submission.id,
      submission.payload,
      submission.payload_sha256,
      accepted_at
    );
    candidate_sha := pg_catalog.encode(
      extensions.digest(pg_catalog.convert_to(candidate::text, 'UTF8'), 'sha256'),
      'hex'
    );

    insert into private.community_observation_candidates (
      submission_id,
      observation_id,
      device_id,
      observation,
      observation_sha256,
      source_payload_sha256,
      created_by,
      created_at
    ) values (
      submission.id,
      candidate ->> 'observation_id',
      submission.device_id,
      candidate,
      candidate_sha,
      submission.payload_sha256,
      request_user,
      accepted_at
    );

    insert into private.submission_moderation (
      submission_id,
      reviewer_id,
      validation_errors,
      decision_reason,
      updated_at
    ) values (
      submission.id,
      request_user,
      '[]'::jsonb,
      reason,
      accepted_at
    )
    on conflict (submission_id) do update
    set reviewer_id = excluded.reviewer_id,
        validation_errors = excluded.validation_errors,
        decision_reason = excluded.decision_reason,
        updated_at = excluded.updated_at;

    perform pg_catalog.set_config('compatforge.transition_reason', reason, true);
    update public.evidence_submissions set state = 'accepted' where id = submission.id;
    return 'accepted';
  end if;

  raise exception 'unsupported review action';
end;
$$;

revoke all on function private.review_community_submission_impl(uuid, text, text) from public, anon;
grant execute on function private.review_community_submission_impl(uuid, text, text) to authenticated;

create or replace function public.review_community_submission(
  submission_id uuid,
  review_action text,
  decision_reason text default null
)
returns public.submission_state
language sql
security invoker
set search_path = ''
as $$
  select private.review_community_submission_impl(
    submission_id,
    review_action,
    decision_reason
  );
$$;

revoke all on function public.review_community_submission(uuid, text, text) from public, anon;
grant execute on function public.review_community_submission(uuid, text, text) to authenticated;

create or replace function private.get_community_publication_batch_impl()
returns table (
  submission_id uuid,
  observation_id text,
  observation jsonb,
  observation_sha256 text,
  source_payload_sha256 text,
  created_at timestamptz
)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
  if auth.uid() is null or private.get_current_moderator_role() is distinct from 'admin' then
    raise exception 'admin authorization required';
  end if;

  return query
  select
    candidate.submission_id,
    candidate.observation_id,
    candidate.observation,
    candidate.observation_sha256,
    candidate.source_payload_sha256,
    candidate.created_at
  from private.community_observation_candidates candidate
  join public.evidence_submissions submission
    on submission.id = candidate.submission_id
  where submission.state = 'accepted'
    and candidate.published_at is null
  order by candidate.created_at asc
  limit 200;
end;
$$;

revoke all on function private.get_community_publication_batch_impl() from public, anon;
grant execute on function private.get_community_publication_batch_impl() to authenticated;

create or replace function public.get_community_publication_batch()
returns table (
  submission_id uuid,
  observation_id text,
  observation jsonb,
  observation_sha256 text,
  source_payload_sha256 text,
  created_at timestamptz
)
language sql
stable
security invoker
set search_path = ''
as $$
  select * from private.get_community_publication_batch_impl();
$$;

revoke all on function public.get_community_publication_batch() from public, anon;
grant execute on function public.get_community_publication_batch() to authenticated;

create or replace function private.publish_community_submission_impl(
  requested_submission_id uuid,
  snapshot_commit_sha text,
  expected_observation_sha256 text
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  request_user uuid := auth.uid();
  moderator_role text := private.get_current_moderator_role();
  submission public.evidence_submissions%rowtype;
  candidate private.community_observation_candidates%rowtype;
  normalized_snapshot_sha text := pg_catalog.lower(pg_catalog.btrim(snapshot_commit_sha));
  normalized_expected_sha text := pg_catalog.lower(pg_catalog.btrim(expected_observation_sha256));
begin
  if request_user is null or moderator_role is distinct from 'admin' then
    raise exception 'admin authorization required';
  end if;

  if normalized_snapshot_sha is null
    or normalized_snapshot_sha !~ '^[0-9a-f]{40}$' then
    raise exception 'snapshot commit SHA must be a full 40 character Git commit SHA';
  end if;

  if normalized_expected_sha is null
    or normalized_expected_sha !~ '^[0-9a-f]{64}$' then
    raise exception 'expected observation SHA-256 must be 64 lowercase hex characters';
  end if;

  select *
  into submission
  from public.evidence_submissions source
  where source.id = requested_submission_id
  for update;

  if not found then
    raise exception 'submission not found';
  end if;

  if submission.state <> 'accepted' then
    raise exception 'publish requires accepted state';
  end if;

  select *
  into candidate
  from private.community_observation_candidates source
  where source.submission_id = submission.id
  for update;

  if not found then
    raise exception 'accepted submission has no canonical observation candidate';
  end if;

  if candidate.published_at is not null then
    raise exception 'canonical observation candidate is already published';
  end if;

  if candidate.observation_sha256 <> normalized_expected_sha then
    raise exception 'observation SHA-256 does not match the accepted candidate';
  end if;

  update private.community_observation_candidates
  set published_at = pg_catalog.now(),
      published_by = request_user,
      snapshot_commit_sha = normalized_snapshot_sha
  where submission_id = submission.id;

  perform pg_catalog.set_config(
    'compatforge.transition_reason',
    'Published after reviewed static snapshot commit ' || normalized_snapshot_sha || '.',
    true
  );

  update public.evidence_submissions
  set state = 'published',
      published_observation_id = candidate.observation_id
  where id = submission.id;

  return candidate.observation_id;
end;
$$;

revoke all on function private.publish_community_submission_impl(uuid, text, text)
  from public, anon;
grant execute on function private.publish_community_submission_impl(uuid, text, text)
  to authenticated;

create or replace function public.publish_community_submission(
  submission_id uuid,
  snapshot_commit_sha text,
  expected_observation_sha256 text
)
returns text
language sql
security invoker
set search_path = ''
as $$
  select private.publish_community_submission_impl(
    submission_id,
    snapshot_commit_sha,
    expected_observation_sha256
  );
$$;

revoke all on function public.publish_community_submission(uuid, text, text) from public, anon;
grant execute on function public.publish_community_submission(uuid, text, text) to authenticated;

create or replace function public.get_moderator_role()
returns text
language sql
stable
security invoker
set search_path = ''
as $$
  select private.get_current_moderator_role();
$$;

revoke all on function public.get_moderator_role() from public, anon;
grant execute on function public.get_moderator_role() to authenticated;
