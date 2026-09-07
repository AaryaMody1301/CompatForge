select
    device_id,
    vendor_id,
    vendor_name,
    product_id,
    product_name,
    interface_type,
    identity_source,
    source_sha256
from {{ ref('int_device_identity') }}
order by device_id
