-- Harden existing hosted installations without rewriting applied migrations.
-- A missing moderator membership must be false, never SQL NULL.
create or replace function private.can_prepare_community_refresh()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select coalesce(
    auth.uid() is not null
    and (
      coalesce(private.get_current_moderator_role() = 'admin', false)
      or exists (
        select 1 from private.refresh_automation_memberships membership
        where membership.user_id = auth.uid()
      )
    ),
    false
  );
$$;

create or replace function private.get_community_refresh_batch_impl()
returns table (
  submission_id uuid, observation_id text, device_id text,
  observation jsonb, observation_text text, observation_sha256 text,
  source_payload_sha256 text, created_at timestamptz
)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
  if private.can_prepare_community_refresh() is not true then
    raise exception 'community refresh authorization required';
  end if;

  return query
  select candidate.submission_id, candidate.observation_id, candidate.device_id,
    candidate.observation, candidate.observation::text,
    candidate.observation_sha256, candidate.source_payload_sha256, candidate.created_at
  from private.community_observation_candidates candidate
  join public.evidence_submissions submission on submission.id = candidate.submission_id
  where submission.state = 'accepted' and candidate.published_at is null
  order by candidate.created_at asc, candidate.observation_id asc
  limit 200;
end;
$$;

-- All writes, including direct authenticated RPCs, pass through this trigger.
create or replace function private.community_only_keys(document jsonb, allowed text[])
returns boolean
language sql
immutable
set search_path = ''
as $$
  select pg_catalog.jsonb_typeof(document) = 'object'
    and not exists (
      select 1 from pg_catalog.jsonb_object_keys(document) field
      where field <> all(allowed)
    );
$$;

revoke all on function private.community_only_keys(jsonb,text[]) from public, anon, authenticated;

create or replace function private.community_text_field_valid(
  document jsonb, field_path text[], maximum integer
)
returns boolean
language sql
immutable
set search_path = ''
as $$
  select document #> field_path is null
    or coalesce(
      pg_catalog.jsonb_typeof(document #> field_path) = 'string'
      and pg_catalog.char_length(document #>> field_path) between 1 and maximum,
      false
    );
$$;

revoke all on function private.community_text_field_valid(jsonb,text[],integer)
  from public, anon, authenticated;

create or replace function private.community_array_has_duplicates(document jsonb)
returns boolean
language sql
immutable
set search_path = ''
as $$
  select exists (
    select 1
    from pg_catalog.jsonb_array_elements(document) as item(value)
    group by value
    having pg_catalog.count(*) > 1
  );
$$;

revoke all on function private.community_array_has_duplicates(jsonb)
  from public, anon, authenticated;

create or replace function private.community_https_reference_valid(reference text)
returns boolean
language plpgsql
immutable
set search_path = ''
as $function$
declare
  parts text[];
  host text;
  port text;
  address inet;
begin
  if reference is null or pg_catalog.char_length(reference) > 2000 then
    return false;
  end if;

  parts := pg_catalog.regexp_match(reference, $uri$^https://(\[[0-9A-Fa-f:.]+\]|(?:[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?)(?:\.(?:[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?))*)(?::([0-9]{1,5}))?(?:/[A-Z0-9._~!$&'()*+,;=:@%/-]*)?(?:\?[A-Z0-9._~!$&'()*+,;=:@%/?-]*)?(?:#[A-Z0-9._~!$&'()*+,;=:@%/?-]*)?$$uri$, 'i');
  if parts is null or reference ~ '%($|[^0-9A-Fa-f]|[0-9A-Fa-f]$)' then
    return false;
  end if;

  host := parts[1];
  port := parts[2];
  if port is not null and port::integer not between 1 and 65535 then
    return false;
  end if;
  if host like '[%' then
    begin
      address := pg_catalog.substr(host, 2, pg_catalog.char_length(host) - 2)::inet;
    exception when others then
      return false;
    end;
    if pg_catalog.family(address) <> 6 then
      return false;
    end if;
  end if;

  return true;
end;
$function$;

revoke all on function private.community_https_reference_valid(text)
  from public, anon, authenticated;

create or replace function private.validate_community_submission_insert()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  payload jsonb := new.payload;
  observed_at timestamptz;
  prepared_at timestamptz;
  field_name text;
  item jsonb;
begin
  if pg_catalog.jsonb_typeof(payload) is distinct from 'object'
    or payload ->> 'record_type' is distinct from 'community_evidence_submission'
    or payload ->> 'schema_version' is distinct from '1.0.0'
    or pg_catalog.jsonb_typeof(payload -> 'configuration') is distinct from 'object'
    or pg_catalog.jsonb_typeof(payload -> 'reproduction') is distinct from 'object'
    or pg_catalog.jsonb_typeof(payload -> 'handoff') is distinct from 'object'
    or pg_catalog.jsonb_typeof(payload -> 'publication') is distinct from 'object'
    or pg_catalog.jsonb_typeof(payload -> 'privacy') is distinct from 'object'
    or pg_catalog.jsonb_typeof(payload -> 'references') is distinct from 'array'
    or pg_catalog.jsonb_typeof(payload #> '{configuration,host}') is distinct from 'object'
    or pg_catalog.jsonb_typeof(payload #> '{configuration,operating_system}') is distinct from 'object'
    or pg_catalog.jsonb_typeof(payload #> '{configuration,drivers}') is distinct from 'array'
    or pg_catalog.jsonb_typeof(payload #> '{reproduction,conditions}') is distinct from 'array'
    or pg_catalog.jsonb_typeof(payload #> '{reproduction,limitations}') is distinct from 'array'
    or pg_catalog.jsonb_typeof(payload #> '{reproduction,steps_summary}') is distinct from 'string'
    or pg_catalog.char_length(payload #>> '{reproduction,steps_summary}') not between 20 and 4000
    or pg_catalog.jsonb_array_length(payload #> '{reproduction,limitations}') < 1
    or coalesce(payload #>> '{configuration,operating_system,family}' in
      ('windows', 'macos', 'ubuntu', 'linux', 'unknown'), false) is not true
    or pg_catalog.jsonb_typeof(payload #> '{configuration,operating_system,version}') is distinct from 'string'
    or pg_catalog.btrim(coalesce(payload #>> '{configuration,operating_system,version}', '')) = ''
    or coalesce(payload #>> '{configuration,architecture}' in
      ('x86_64', 'arm64', 'unknown'), false) is not true
    or coalesce(payload #>> '{configuration,connection_path}' in
      ('direct_port', 'usb_hub', 'unspecified'), false) is not true
    or payload #>> '{publication,consent_version}' is distinct from '1.0'
    or payload #>> '{handoff,schema_version}' is distinct from '1.0.0'
    or coalesce(payload #>> '{handoff,sha256}' ~ '^[0-9a-f]{64}$', false) is not true
    or payload ->> 'client_submission_id' is distinct from new.client_submission_id::text
    or payload ->> 'target_device_id' is distinct from new.device_id
    or payload #>> '{reproduction,outcome}' is distinct from new.observed_outcome
    or (payload #>> '{reproduction,outcome}' = 'works_with_conditions'
      and pg_catalog.jsonb_array_length(payload #> '{reproduction,conditions}') = 0)
  then
    raise exception 'invalid community submission contract';
  end if;

  if not private.community_only_keys(payload, array[
    'record_type', 'schema_version', 'client_submission_id', 'prepared_at',
    'evidence_ready', 'target_device_id', 'handoff', 'configuration',
    'reproduction', 'publication', 'privacy', 'references'
  ]) or not private.community_only_keys(payload -> 'handoff', array[
    'schema_version', 'sha256', 'user_approved_export'
  ]) or not private.community_only_keys(payload -> 'configuration', array[
    'host', 'operating_system', 'architecture', 'connection_path', 'drivers'
  ]) or not private.community_only_keys(payload #> '{configuration,host}', array[
    'manufacturer', 'model'
  ]) or not private.community_only_keys(payload #> '{configuration,operating_system}', array[
    'family', 'version', 'build'
  ]) or not private.community_only_keys(payload -> 'reproduction', array[
    'outcome', 'observed_at', 'steps_summary', 'conditions', 'limitations',
    'firmware_version', 'software_version'
  ]) or not private.community_only_keys(payload -> 'publication', array[
    'anonymized_publication', 'consent_version'
  ]) or not private.community_only_keys(payload -> 'privacy', array[
    'contains_raw_diagnostic', 'contains_serial_numbers',
    'contains_network_identifiers', 'contains_unrelated_usb_inventory',
    'automatic_publication'
  ]) then
    raise exception 'unknown fields in community submission';
  end if;

  if pg_catalog.jsonb_array_length(payload #> '{configuration,drivers}') > 10
    or pg_catalog.jsonb_array_length(payload #> '{reproduction,conditions}') > 20
    or pg_catalog.jsonb_array_length(payload #> '{reproduction,limitations}') > 20
    or pg_catalog.jsonb_array_length(payload -> 'references') > 5
    or pg_catalog.char_length(payload #>> '{configuration,operating_system,version}') > 100
  then
    raise exception 'community submission exceeds contract limits';
  end if;
  if private.community_array_has_duplicates(payload #> '{configuration,drivers}')
    or private.community_array_has_duplicates(payload #> '{reproduction,conditions}')
    or private.community_array_has_duplicates(payload #> '{reproduction,limitations}')
    or private.community_array_has_duplicates(payload -> 'references') then
    raise exception 'duplicate items in community submission';
  end if;
  if not private.community_text_field_valid(payload, '{configuration,host,manufacturer}', 200)
    or not private.community_text_field_valid(payload, '{configuration,host,model}', 200)
    or not private.community_text_field_valid(payload, '{configuration,operating_system,build}', 100)
    or not private.community_text_field_valid(payload, '{reproduction,firmware_version}', 200)
    or not private.community_text_field_valid(payload, '{reproduction,software_version}', 200) then
    raise exception 'invalid optional community submission metadata';
  end if;
  for item in select value from pg_catalog.jsonb_array_elements(payload #> '{configuration,drivers}') loop
    if not private.community_only_keys(item, array['name', 'provider', 'version'])
      or item = '{}'::jsonb then
      raise exception 'invalid driver object';
    end if;
    foreach field_name in array array['name', 'provider', 'version'] loop
      if not private.community_text_field_valid(item, array[field_name], 200) then
        raise exception 'invalid driver metadata';
      end if;
    end loop;
  end loop;
  for item in select value from pg_catalog.jsonb_array_elements(payload #> '{reproduction,conditions}') loop
    if pg_catalog.jsonb_typeof(item) is distinct from 'string'
      or pg_catalog.char_length(item #>> '{}') not between 1 and 1000 then
      raise exception 'invalid reproduction condition';
    end if;
  end loop;
  for item in select value from pg_catalog.jsonb_array_elements(payload #> '{reproduction,limitations}') loop
    if pg_catalog.jsonb_typeof(item) is distinct from 'string'
      or pg_catalog.char_length(item #>> '{}') not between 1 and 1000 then
      raise exception 'invalid reproduction limitation';
    end if;
  end loop;
  for item in select value from pg_catalog.jsonb_array_elements(payload -> 'references') loop
    if pg_catalog.jsonb_typeof(item) is distinct from 'string'
      or not private.community_https_reference_valid(item #>> '{}')
      or pg_catalog.char_length(item #>> '{}') > 2000 then
      raise exception 'invalid supporting reference';
    end if;
  end loop;

  -- Require explicit false/true values; malformed JSON booleans must not be
  -- treated as consent or accepted via an implicit text cast.
  if payload -> 'evidence_ready' is distinct from 'false'::jsonb
    or payload #> '{handoff,user_approved_export}' is distinct from 'true'::jsonb
    or payload #> '{publication,anonymized_publication}' is distinct from 'true'::jsonb then
    raise exception 'invalid community submission consent';
  end if;
  foreach field_name in array array[
    'contains_raw_diagnostic', 'contains_serial_numbers',
    'contains_network_identifiers', 'contains_unrelated_usb_inventory',
    'automatic_publication'
  ] loop
    if payload #> array['privacy', field_name] is distinct from 'false'::jsonb then
      raise exception 'invalid community submission privacy declaration';
    end if;
  end loop;

  if pg_catalog.jsonb_typeof(payload -> 'prepared_at') is distinct from 'string'
    or pg_catalog.jsonb_typeof(payload #> '{reproduction,observed_at}') is distinct from 'string'
    or coalesce(payload ->> 'prepared_at' ~ '(Z|[+-][0-9]{2}:[0-9]{2})$', false) is not true
    or coalesce(payload #>> '{reproduction,observed_at}' ~
      '(Z|[+-][0-9]{2}:[0-9]{2})$', false) is not true
  then
    raise exception 'explicit observation and preparation timestamps are required';
  end if;
  begin
    observed_at := (payload #>> '{reproduction,observed_at}')::timestamptz;
    prepared_at := (payload ->> 'prepared_at')::timestamptz;
  exception when others then
    raise exception 'invalid community submission timestamp';
  end;
  if observed_at > pg_catalog.now() + interval '5 minutes'
    or prepared_at > pg_catalog.now() + interval '5 minutes' then
    raise exception 'community submission timestamp cannot be in the future';
  end if;
  return new;
end;
$$;

revoke all on function private.validate_community_submission_insert() from public, anon, authenticated;
create trigger evidence_submissions_validate_contract
before insert on public.evidence_submissions
for each row execute function private.validate_community_submission_insert();

-- Defense in depth: an old malformed or future-dated submission cannot be
-- converted into a new accepted candidate by a moderator after this upgrade.
create or replace function private.validate_community_candidate_insert()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  observed_at timestamptz;
begin
  if pg_catalog.jsonb_typeof(new.observation -> 'observed_at') is distinct from 'string' then
    raise exception 'candidate observation timestamp is required';
  end if;
  begin
    observed_at := (new.observation ->> 'observed_at')::timestamptz;
  exception when others then
    raise exception 'candidate observation timestamp is invalid';
  end;
  if observed_at > pg_catalog.now() + interval '5 minutes' then
    raise exception 'candidate observation timestamp cannot be in the future';
  end if;
  return new;
end;
$$;

revoke all on function private.validate_community_candidate_insert() from public, anon, authenticated;
create trigger community_candidate_validate_timestamp
before insert on private.community_observation_candidates
for each row execute function private.validate_community_candidate_insert();

-- Serialize inserts for the same submitter before counting the rolling window.
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
  perform 1 from auth.users where id = new.submitter_id for update;
  select
    count(*) filter (where submission.created_at >= pg_catalog.now() - interval '1 hour')::integer,
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
