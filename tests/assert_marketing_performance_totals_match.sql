-- fails if any total in the mart differs from the fact tables it was built from
with mart as (
    select
        coalesce(sum(spend), 0) as spend,
        sum(sessions) as sessions,
        sum(purchase_revenue_usd) as purchase_revenue,
        sum(first_touch_revenue_usd) as first_touch,
        sum(last_touch_revenue_usd) as last_touch,
        sum(linear_revenue_usd) as linear,
        sum(position_based_revenue_usd) as position_based
    from {{ ref('marketing_performance') }}
),

src_spend as (
    select coalesce(sum(spend), 0) as spend
    from {{ ref('fact_ad_spend') }}
),

src_sessions as (
    select
        count(*) as sessions,
        coalesce(sum(purchase_revenue_usd), 0) as purchase_revenue
    from {{ ref('fact_sessions') }}
),

src_credit as (
    select
        sum(if(attribution_model = 'first_touch', attributed_revenue_usd, 0)) as first_touch,
        sum(if(attribution_model = 'last_touch', attributed_revenue_usd, 0)) as last_touch,
        sum(if(attribution_model = 'linear', attributed_revenue_usd, 0)) as linear,
        sum(if(attribution_model = 'position_based', attributed_revenue_usd, 0)) as position_based
    from {{ ref('fact_attribution_credit') }}
)

select
    m.spend as mart_spend,
    sp.spend as source_spend,
    m.sessions as mart_sessions,
    ss.sessions as source_sessions,
    m.purchase_revenue as mart_purchase_revenue,
    ss.purchase_revenue as source_purchase_revenue
from mart m
cross join src_spend sp
cross join src_sessions ss
cross join src_credit c
where abs(m.spend - sp.spend) > 0.01
   or m.sessions != ss.sessions
   or abs(m.purchase_revenue - ss.purchase_revenue) > 0.01
   or abs(m.first_touch - c.first_touch) > 0.01
   or abs(m.last_touch - c.last_touch) > 0.01
   or abs(m.linear - c.linear) > 0.01
   or abs(m.position_based - c.position_based) > 0.01