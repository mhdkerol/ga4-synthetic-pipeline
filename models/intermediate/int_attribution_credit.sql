{{ config(materialized='table') }}

with sessions as (
    select
        session_key,
        user_pseudo_id,
        session_start_ts,
        session_date,
        channel,
        has_purchase,
        purchase_revenue_usd
    from {{ ref('int_sessions') }}
),

-- each purchasing session is one conversion
conversions as (
    select
        session_key as conversion_session_key,
        user_pseudo_id,
        session_start_ts as conversion_ts,
        purchase_revenue_usd as conversion_revenue_usd
    from sessions
    where has_purchase
),

-- for each conversion, the user's journey = all their sessions up to and including it
touchpoints as (
    select
        c.conversion_session_key,
        c.conversion_revenue_usd,
        s.session_key as touch_session_key,
        s.user_pseudo_id,
        s.session_date as touch_date,
        s.channel,
        row_number() over (
            partition by c.conversion_session_key
            order by s.session_start_ts, s.session_key
        ) as touch_position,
        count(*) over (partition by c.conversion_session_key) as touch_count
    from conversions c
    join sessions s
        on s.user_pseudo_id = c.user_pseudo_id
       and s.session_start_ts <= c.conversion_ts
),

credited as (
    select
        *,
        'first_touch' as attribution_model,
        if(touch_position = 1, 1.0, 0.0) as credit
    from touchpoints

    union all

    select
        *,
        'last_touch',
        if(touch_position = touch_count, 1.0, 0.0)
    from touchpoints

    union all

    select
        *,
        'linear',
        1.0 / touch_count
    from touchpoints

    union all

    select
        *,
        'position_based',
        case
            when touch_count = 1 then 1.0
            when touch_count = 2 then 0.5
            when touch_position in (1, touch_count) then 0.4
            else 0.2 / (touch_count - 2)
        end
    from touchpoints
)

select
    concat(conversion_session_key, '|', attribution_model, '|', touch_session_key) as credit_key,
    conversion_session_key,
    touch_session_key,
    user_pseudo_id,
    touch_date,
    channel,
    touch_position,
    touch_count,
    attribution_model,
    credit,
    credit * conversion_revenue_usd as attributed_revenue_usd
from credited
where credit > 0