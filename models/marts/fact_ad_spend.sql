select
    c.channel_key,
    s.spend_date,
    s.spend,
    s.impressions,
    s.clicks,
    s.campaign_count
from {{ ref('int_channel_daily_spend') }} s
left join {{ ref('dim_channel') }} c
    on c.channel_name = s.channel