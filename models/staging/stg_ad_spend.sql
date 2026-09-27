with source as (
    select * from {{ source('ga4_synthetic_raw', 'raw_ad_spend') }}
),

cleaned as (
    select
        parse_date('%Y%m%d', cast(event_date as string)) as spend_date,
        initcap(channel) as channel,
        campaign,
        impressions,
        clicks,
        case when spend < 0 then null else spend end as spend
    from source
),

deduped as (
    select
        *,
        row_number() over (
            partition by spend_date, channel, campaign
            order by spend_date
        ) as rn
    from cleaned
)

select * except(rn)
from deduped
where rn = 1