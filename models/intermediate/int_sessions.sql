{{ config(materialized='table') }}

with events as (
    select
        *,
        parse_date('%Y%m%d', cast(event_date as string)) as event_dt
    from {{ ref('stg_ga4_events') }}
    where user_pseudo_id is not null
      and ga_session_id is not null
)

select
    concat(user_pseudo_id, '-', cast(ga_session_id as string)) as session_key,
    user_pseudo_id,
    ga_session_id,
    min(ga_session_number) as ga_session_number,
    min(event_dt) as session_date,
    timestamp_micros(min(event_timestamp)) as session_start_ts,
    timestamp_micros(max(event_timestamp)) as session_end_ts,
    array_agg(channel ignore nulls order by event_timestamp limit 1)[safe_offset(0)] as channel,
    array_agg(traffic_source ignore nulls order by event_timestamp limit 1)[safe_offset(0)] as traffic_source,
    array_agg(device_category ignore nulls order by event_timestamp limit 1)[safe_offset(0)] as device_category,
    array_agg(country ignore nulls order by event_timestamp limit 1)[safe_offset(0)] as country,
    count(*) as event_count,
    countif(event_name = 'page_view') as page_view_count,
    coalesce(sum(engagement_time_msec), 0) as engagement_time_msec,
    logical_or(event_name = 'purchase') as has_purchase,
    count(distinct if(event_name = 'purchase', transaction_id, null)) as transaction_count,
    coalesce(sum(if(event_name = 'purchase', purchase_revenue, 0)), 0) as purchase_revenue_usd
from events
group by user_pseudo_id, ga_session_id