select
    s.statement_id,
    s.device_id,
    s.architecture,
    s.os_family,
    s.version_mode,
    s.versions_json,
    s.minimum_version,
    s.connection_kind,
    s.minimum_usb_generation,
    case when s.driver_name is null then null else md5(lower(s.driver_name) || '|' || coalesce(lower(s.driver_version), '')) end as driver_key,
    case when s.software_name is null then null else md5(lower(s.software_name) || '|' || coalesce(lower(s.software_version), '')) end as software_key,
    md5('support|' || s.connection_kind || '|' || coalesce(s.minimum_usb_generation, '')) as connection_key,
    s.support_status,
    s.conditions_json,
    s.evidence_source_type,
    s.sources_json,
    s.source_note,
    strftime(s.reviewed_at, '%Y-%m-%dT%H:%M:%SZ') as reviewed_at,
    strftime(s.recorded_at, '%Y-%m-%dT%H:%M:%SZ') as recorded_at,
    f.age_days,
    f.freshness_status,
    s.limitations_json,
    s.record_sha256
from {{ ref('stg_support_statements') }} s
join {{ ref('int_evidence_freshness') }} f
    on f.evidence_kind = 'support_statement'
   and f.evidence_id = s.statement_id
