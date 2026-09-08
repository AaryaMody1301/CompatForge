-- Keep accepted community evidence provenance tied to the reviewed repository
-- rather than an unverified custom domain. The URL becomes resolvable only
-- after the exact candidate is merged into the canonical static evidence path.
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
      'source_url', 'https://github.com/AaryaMody1301/CompatForge/blob/main/data/evidence/observations/' || observation_id || '.json',
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
