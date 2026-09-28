{{ config(materialized='table') }}

select
    session_date,
    channel,
    count(*) as sessions,
    count(distinct user_pseudo_id) as users,
    countif(ga_session_number = 1) as first_sessions,
    countif(has_purchase) as converting_sessions,
    sum(purchase_revenue_usd) as purchase_revenue_usd
from {{ ref('int_sessions') }}
group by session_date, channel