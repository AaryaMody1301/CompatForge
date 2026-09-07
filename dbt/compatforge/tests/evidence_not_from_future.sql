select *
from {{ ref('int_evidence_freshness') }}
where age_days < 0
