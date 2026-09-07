with software as (
    select software_name, software_version from {{ ref('stg_compatibility_observations') }}
    union
    select software_name, software_version from {{ ref('stg_support_statements') }}
)
select distinct
    md5(lower(software_name) || '|' || coalesce(lower(software_version), '')) as software_key,
    software_name,
    software_version
from software
where software_name is not null
