select device_id
from {{ ref('device_catalog') }}
where not regexp_matches(device_id, '^usb:[0-9A-F]{4}:[0-9A-F]{4}$')
