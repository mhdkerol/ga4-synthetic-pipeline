select
    s.session_key,
    c.channel_key,
    s.session_date,
    s.user_pseudo_id,
    s.session_start_ts,
    s.session_end_ts,
    timestamp_diff(s.session_end_ts, s.session_start_ts, second) as session_duration_seconds,
    s.ga_session_number,
    s.traffic_source,
    s.device_category,
    s.country,
    s.event_count,
    s.page_view_count,
    s.engagement_time_msec,
    s.transaction_count,
    s.purchase_revenue_usd,
    s.has_purchase
from {{ ref('int_sessions') }} s
left join {{ ref('dim_channel') }} c
    on c.channel_name = s.channel