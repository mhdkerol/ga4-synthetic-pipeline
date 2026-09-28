select
    conversion_session_key,
    attribution_model,
    sum(credit) as total_credit
from {{ ref('int_attribution_credit') }}
group by 1, 2
having abs(sum(credit) - 1) > 0.0001