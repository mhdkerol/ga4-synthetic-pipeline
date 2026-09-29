with session_channels as (
    select distinct channel
    from {{ ref('int_channel_daily_sessions') }}
),

spend_channels as (
    select distinct channel
    from {{ ref('int_channel_daily_spend') }}
),

-- every channel that shows up in either source, listed once
all_channels as (
    select channel from session_channels
    union distinct
    select channel from spend_channels
)

select
    {{ dbt_utils.generate_surrogate_key(['a.channel']) }} as channel_key,
    a.channel as channel_name,
    case
        when a.channel in ('Paid Search', 'Social') then 'Paid'
        when a.channel in ('Direct', 'Email', 'Organic Search', 'Referral') then 'Unpaid'
        else 'Unmapped'
    end as channel_type,
    s.channel is not null as has_sessions,
    p.channel is not null as has_ad_spend
from all_channels a
left join session_channels s on s.channel = a.channel
left join spend_channels p on p.channel = a.channel