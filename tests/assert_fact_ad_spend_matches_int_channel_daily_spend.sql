-- returns a row (and fails) if the fact lost, added or changed anything vs the intermediate model
with fact as (
    select count(*) as row_count, coalesce(sum(spend), 0) as spend
    from {{ ref('fact_ad_spend') }}
),

source as (
    select count(*) as row_count, coalesce(sum(spend), 0) as spend
    from {{ ref('int_channel_daily_spend') }}
)

select
    f.row_count as fact_rows,
    s.row_count as source_rows,
    f.spend as fact_spend,
    s.spend as source_spend
from fact f
cross join source s
where f.row_count != s.row_count
   or abs(f.spend - s.spend) > 0.001