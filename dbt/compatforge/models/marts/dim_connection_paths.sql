with connections as (
    select
        'observed' as connection_scope,
        connection_signature as connection_value
    from {{ ref('stg_compatibility_observations') }}
    union
    select
        'support' as connection_scope,
        connection_kind || '|' || coalesce(minimum_usb_generation, '') as connection_value
    from {{ ref('stg_support_statements') }}
)
select distinct
    md5(connection_scope || '|' || connection_value) as connection_key,
    connection_scope,
    connection_value
from connections
