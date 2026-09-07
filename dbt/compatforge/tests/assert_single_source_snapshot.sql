select count(distinct source_sha256) as source_snapshot_count
from {{ ref('device_catalog') }}
having count(distinct source_sha256) != 1
