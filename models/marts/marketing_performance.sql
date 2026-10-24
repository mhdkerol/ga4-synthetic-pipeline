with spine as (
    -- every channel with every day: 6 x 90 = 540 rows
    select
        c.channel_key,
        c.channel_name,
        c.channel_type,
        d.date_day,
        d.month_name,
        d.day_of_week_name,
        d.week_start_date
    from {{ ref('dim_channel') }} c
    cross join {{ ref('dim_date') }} d
),

spend as (
    -- already one row per channel per day
    select
        channel_key,
        spend_date,
        spend,
        impressions,
        clicks
    from {{ ref('fact_ad_spend') }}
),

sessions as (
    -- one row per session, rolled up to one row per channel per day
    select
        channel_key,
        session_date,
        count(*) as sessions,
        countif(has_purchase) as purchasing_sessions,
        sum(purchase_revenue_usd) as purchase_revenue_usd
    from {{ ref('fact_sessions') }}
    group by channel_key, session_date
),

attributed as (
    -- one row per credited touch per model, rolled up to channel per touch day,
    -- with one column per model
    select
        channel_key,
        touch_date,
        sum(if(attribution_model = 'first_touch', attributed_revenue_usd, 0)) as first_touch_revenue_usd,
        sum(if(attribution_model = 'last_touch', attributed_revenue_usd, 0)) as last_touch_revenue_usd,
        sum(if(attribution_model = 'linear', attributed_revenue_usd, 0)) as linear_revenue_usd,
        sum(if(attribution_model = 'position_based', attributed_revenue_usd, 0)) as position_based_revenue_usd
    from {{ ref('fact_attribution_credit') }}
    group by channel_key, touch_date
)

select
    p.channel_key,
    p.date_day,
    p.channel_name,
    p.channel_type,
    p.month_name,
    p.day_of_week_name,
    p.week_start_date,
    sp.spend,
    sp.impressions,
    sp.clicks,
    coalesce(s.sessions, 0) as sessions,
    coalesce(s.purchasing_sessions, 0) as purchasing_sessions,
    coalesce(s.purchase_revenue_usd, 0) as purchase_revenue_usd,
    coalesce(a.first_touch_revenue_usd, 0) as first_touch_revenue_usd,
    coalesce(a.last_touch_revenue_usd, 0) as last_touch_revenue_usd,
    coalesce(a.linear_revenue_usd, 0) as linear_revenue_usd,
    coalesce(a.position_based_revenue_usd, 0) as position_based_revenue_usd
from spine p
left join spend sp
    on sp.channel_key = p.channel_key
    and sp.spend_date = p.date_day
left join sessions s
    on s.channel_key = p.channel_key
    and s.session_date = p.date_day
left join attributed a
    on a.channel_key = p.channel_key
    and a.touch_date = p.date_day