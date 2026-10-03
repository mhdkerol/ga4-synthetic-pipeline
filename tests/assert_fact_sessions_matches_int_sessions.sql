-- returns a row (and fails) if the fact lost, added or changed anything vs int_sessions
with fact as (
    select count(*) as row_count, sum(purchase_revenue_usd) as revenue
    from {{ ref('fact_sessions') }}
),

source as (
    select count(*) as row_count, sum(purchase_revenue_usd) as revenue
    from {{ ref('int_sessions') }}
)

select
    f.row_count as fact_rows,
    s.row_count as source_rows,
    f.revenue as fact_revenue,
    s.revenue as source_revenue
from fact f
cross join source s
where f.row_count != s.row_count
   or abs(f.revenue - s.revenue) > 0.001