{{ config(materialized='table') }}

select
    spend_date,
    channel,
    sum(spend) as spend,
    sum(impressions) as impressions,
    sum(clicks) as clicks,
    count(distinct campaign) as campaign_count
from {{ ref('stg_ad_spend') }}
group by spend_date, channel