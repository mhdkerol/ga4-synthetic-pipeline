with source as (
    select * from {{ source('ga4_synthetic_raw', 'raw_ga4_events') }}
),

renamed as (
    select
        event_date,
        event_timestamp,
        event_name,
        nullif(user_pseudo_id, '') as user_pseudo_id,
        user_first_touch_timestamp,
        device.category as device_category,
        device.operating_system as device_operating_system,
        device.web_info.browser as browser,
        initcap(geo.country) as country,
        geo.city as city,
        traffic_source.medium as channel,
        traffic_source.source as traffic_source,
        (select value.int_value from unnest(event_params) where key = 'ga_session_id') as ga_session_id,
        (select value.int_value from unnest(event_params) where key = 'ga_session_number') as ga_session_number,
        (select value.string_value from unnest(event_params) where key = 'page_location') as page_location,
        (select value.string_value from unnest(event_params) where key = 'page_title') as page_title,
        (select value.int_value from unnest(event_params) where key = 'engagement_time_msec') as engagement_time_msec,
        (select value.double_value from unnest(event_params) where key = 'value') as event_value_raw,
        (select value.string_value from unnest(event_params) where key = 'currency') as event_currency,
        (select value.string_value from unnest(event_params) where key = 'discount_code') as discount_code,
        ecommerce.transaction_id,
        ecommerce.purchase_revenue
    from source
),

converted as (
    select
        * except(event_value_raw, event_currency),
        event_value_raw as event_value_usd,
        {{ normalize_currency_to_usd('event_currency') }} as currency
    from renamed
),

deduped as (
    select
        *,
        row_number() over (
            partition by user_pseudo_id, ga_session_id, event_name, event_timestamp
            order by event_timestamp
        ) as rn
    from converted
)

select * except(rn)
from deduped
where rn = 1