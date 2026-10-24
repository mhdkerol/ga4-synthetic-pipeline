-- fails on any channel-day where last-touch revenue differs from purchase revenue
select
    channel_key,
    date_day,
    purchase_revenue_usd,
    last_touch_revenue_usd
from {{ ref('marketing_performance') }}
where abs(purchase_revenue_usd - last_touch_revenue_usd) > 0.01