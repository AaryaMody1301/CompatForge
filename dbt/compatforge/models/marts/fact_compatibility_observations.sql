select
    o.observation_id,
    o.device_id,
    md5(lower(o.host_manufacturer) || '|' || lower(o.host_model) || '|' || o.architecture) as host_key,
    md5(o.os_family || '|' || o.os_version || '|' || coalesce(o.os_build, '')) as os_key,
    case when o.driver_name is null then null else md5(lower(o.driver_name) || '|' || coalesce(lower(o.driver_version), '')) end as driver_key,
    case when o.software_name is null then null else md5(lower(o.software_name) || '|' || coalesce(lower(o.software_version), '')) end as software_key,
    md5('observed|' || o.connection_signature) as connection_key,
    o.architecture,
    o.os_family,
    o.os_version,
    o.os_build,
    o.connection_signature,
    o.connection_path_json,
    o.firmware_version,
    o.outcome,
    o.conditions_json,
    o.evidence_source_type,
    o.source_url,
    o.source_title,
    strftime(o.observed_at, '%Y-%m-%dT%H:%M:%SZ') as observed_at,
    strftime(o.recorded_at, '%Y-%m-%dT%H:%M:%SZ') as recorded_at,
    f.age_days,
    f.freshness_status,
    o.limitations_json,
    o.notes,
    o.record_sha256
from {{ ref('stg_compatibility_observations') }} o
join {{ ref('int_evidence_freshness') }} f
    on f.evidence_kind = 'observation'
   and f.evidence_id = o.observation_id
