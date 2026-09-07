select
    trim(device_id) as device_id,
    upper(trim(vendor_id)) as vendor_id,
    upper(trim(product_id)) as product_id,
    trim(product_name) as product_name,
    cast(source_line as bigint) as source_line,
    source_sha256
from {{ source('bronze', 'usb_devices') }}
