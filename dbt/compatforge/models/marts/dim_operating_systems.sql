select distinct
    md5(os_family || '|' || os_version || '|' || coalesce(os_build, '')) as os_key,
    os_family,
    os_version,
    os_build
from {{ ref('stg_compatibility_observations') }}
