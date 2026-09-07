with reference_time as (
    select as_of from {{ ref('stg_evidence_run_metadata') }}
), evidence as (
    select
        'observation' as evidence_kind,
        observation_id as evidence_id,
        device_id,
        observed_at as evidence_at
    from {{ ref('stg_compatibility_observations') }}
    union all
    select
        'support_statement' as evidence_kind,
        statement_id as evidence_id,
        device_id,
        reviewed_at as evidence_at
    from {{ ref('stg_support_statements') }}
), aged as (
    select
        evidence.*,
        date_diff('day', evidence.evidence_at, reference_time.as_of) as age_days
    from evidence
    cross join reference_time
)
select
    evidence_kind,
    evidence_id,
    device_id,
    evidence_at,
    age_days,
    case
        when age_days <= 180 then 'fresh'
        when age_days <= 365 then 'aging'
        else 'stale'
    end as freshness_status
from aged
