select
    upper(trim(vendor_id)) as vendor_id,
    trim(vendor_name) as vendor_name,
    cast(source_line as bigint) as source_line,
    source_sha256
from {{ source('bronze', 'usb_vendors') }}
