with drivers as (
    select driver_name, driver_version from {{ ref('stg_compatibility_observations') }}
    union
    select driver_name, driver_version from {{ ref('stg_support_statements') }}
)
select distinct
    md5(lower(driver_name) || '|' || coalesce(lower(driver_version), '')) as driver_key,
    driver_name,
    driver_version
from drivers
where driver_name is not null
