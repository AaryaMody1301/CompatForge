select
    d.device_id,
    d.vendor_id,
    v.vendor_name,
    d.product_id,
    d.product_name,
    'usb' as interface_type,
    'usb.ids' as identity_source,
    d.source_sha256,
    d.source_line
from {{ ref('stg_usb_devices') }} as d
inner join {{ ref('stg_usb_vendors') }} as v
    on d.vendor_id = v.vendor_id
