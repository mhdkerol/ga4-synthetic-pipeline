select
    a.credit_key,
    a.conversion_session_key,
    a.touch_session_key,
    c.channel_key,
    a.touch_date,
    a.attribution_model,
    a.touch_position,
    a.touch_count,
    a.credit,
    a.attributed_revenue_usd
from {{ ref('int_attribution_credit') }} a
left join {{ ref('dim_channel') }} c
    on c.channel_name = a.channel