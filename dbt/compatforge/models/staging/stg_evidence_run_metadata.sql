select
    cast(as_of as timestamp) as as_of,
    as_of as as_of_iso
from {{ source('bronze', 'evidence_run_metadata') }}
