select distinct
    md5(lower(host_manufacturer) || '|' || lower(host_model) || '|' || architecture) as host_key,
    host_manufacturer,
    host_model,
    architecture
from {{ ref('stg_compatibility_observations') }}
