with date_range as (
    -- earliest and latest day found across both sources
    select
        least(
            (select min(session_date) from {{ ref('int_channel_daily_sessions') }}),
            (select min(spend_date) from {{ ref('int_channel_daily_spend') }})
        ) as start_date,
        greatest(
            (select max(session_date) from {{ ref('int_channel_daily_sessions') }}),
            (select max(spend_date) from {{ ref('int_channel_daily_spend') }})
        ) as end_date
),

-- one row for every day between start and end
calendar as (
    select date_day
    from date_range,
        unnest(generate_date_array(start_date, end_date)) as date_day
),

with_weekday as (
    select
        date_day,
        -- Monday = 1 ... Sunday = 7
        cast(format_date('%u', date_day) as int64) as day_of_week_number
    from calendar
)

select
    date_day,
    extract(year from date_day) as year_number,
    extract(month from date_day) as month_number,
    format_date('%B', date_day) as month_name,
    day_of_week_number,
    format_date('%A', date_day) as day_of_week_name,
    date_trunc(date_day, isoweek) as week_start_date,
    day_of_week_number in (6, 7) as is_weekend
from with_weekday