-- fails if the table is not exactly one row per channel per day
with expected as (
    select
        (select count(*) from {{ ref('dim_channel') }})
        * (select count(*) from {{ ref('dim_date') }}) as expected_rows
),

actual as (
    select count(*) as actual_rows
    from {{ ref('marketing_performance') }}
)

select
    a.actual_rows,
    e.expected_rows
from actual a
cross join expected e
where a.actual_rows != e.expected_rows