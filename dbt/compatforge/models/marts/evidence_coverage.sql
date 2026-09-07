with observations as (
    select
        device_id,
        count(*) as observation_count,
        count(distinct os_family) as observed_os_family_count,
        count(distinct architecture) as observed_architecture_count,
        max(observed_at) as latest_observation_at,
        sum(case when freshness_status = 'stale' then 1 else 0 end) as stale_observation_count
    from {{ ref('fact_compatibility_observations') }}
    group by device_id
), support as (
    select
        device_id,
        count(*) as support_statement_count,
        count(distinct os_family) as supported_os_family_count,
        count(distinct architecture) as supported_architecture_count,
        max(reviewed_at) as latest_support_review_at,
        sum(case when freshness_status = 'stale' then 1 else 0 end) as stale_support_count
    from {{ ref('fact_support_statements') }}
    group by device_id
)
select
    d.device_id,
    d.vendor_id,
    d.vendor_name,
    d.product_id,
    d.product_name,
    coalesce(o.observation_count, 0) as observation_count,
    coalesce(s.support_statement_count, 0) as support_statement_count,
    coalesce(o.observed_os_family_count, 0) as observed_os_family_count,
    coalesce(s.supported_os_family_count, 0) as supported_os_family_count,
    coalesce(o.observed_architecture_count, 0) as observed_architecture_count,
    coalesce(s.supported_architecture_count, 0) as supported_architecture_count,
    o.latest_observation_at,
    s.latest_support_review_at,
    coalesce(o.stale_observation_count, 0) + coalesce(s.stale_support_count, 0) as stale_evidence_count,
    case
        when coalesce(o.observation_count, 0) > 0 and coalesce(s.support_statement_count, 0) > 0 then 'observed_and_supported'
        when coalesce(o.observation_count, 0) > 0 then 'observed_only'
        when coalesce(s.support_statement_count, 0) > 0 then 'support_only'
        else 'unknown'
    end as coverage_state
from {{ ref('device_catalog') }} d
left join observations o using (device_id)
left join support s using (device_id)
