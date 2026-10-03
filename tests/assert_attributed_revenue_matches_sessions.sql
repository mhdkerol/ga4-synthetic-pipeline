-- fails if any model hands out a different total revenue than the purchasing sessions earned,
-- or if one of the four models is missing entirely
with expected as (
    select sum(purchase_revenue_usd) as revenue
    from {{ ref('fact_sessions') }}
    where has_purchase
),

actual as (
    select attribution_model, sum(attributed_revenue_usd) as revenue
    from {{ ref('fact_attribution_credit') }}
    group by attribution_model
)

select
    a.attribution_model as check_name,
    a.revenue as actual_value,
    e.revenue as expected_value
from actual a
cross join expected e
where abs(a.revenue - e.revenue) > 0.01

union all

select
    'expected_4_models' as check_name,
    cast(n as float64) as actual_value,
    4.0 as expected_value
from (
    select count(distinct attribution_model) as n
    from {{ ref('fact_attribution_credit') }}
)
where n != 4