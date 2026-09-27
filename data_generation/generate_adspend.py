"""
ga4-synthetic-pipeline
Synthetic daily ad spend generator — second data source, paired with
ga4_synthetic_events.json.

Generates daily spend/impressions/clicks by channel + campaign, over the
same 90-day window and using the same channel names as the GA4 synthetic
events, so the two sources join cleanly on (event_date, channel) in dbt
for CAC / ROAS calculations.

Output: ga4_synthetic_adspend.csv

Load into BigQuery, no coding required:
  BigQuery Console -> your dataset -> Create Table -> Upload -> select this
  .csv -> Format: CSV -> check "Auto-detect schema" -> check "Header rows
  to skip: 1" -> Create.
"""

import csv
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

# Same channels as the GA4 synthetic events, minus "Direct" (you can't buy direct traffic)
PAID_CHANNELS = ["Organic Search", "Paid Search", "Referral", "Email", "Social"]

# Realistic-ish base costs per channel (cost per click, roughly)
CHANNEL_CPC = {
    "Organic Search": 0.0,   # organic = no media spend, kept for completeness/comparison
    "Paid Search": 1.20,
    "Referral": 0.0,         # unpaid referral traffic
    "Email": 0.05,           # cost of sends, not per-click bidding
    "Social": 0.65,
}

CAMPAIGNS_BY_CHANNEL = {
    "Paid Search": ["Brand_Exact", "Generic_Ecommerce", "Competitor_Terms"],
    "Social": ["Prospecting_Lookalike", "Retargeting_Cart", "Awareness_Video"],
    "Email": ["Weekly_Newsletter", "Abandoned_Cart", "Promo_Blast"],
    "Referral": ["Affiliate_Program"],
    "Organic Search": ["Organic"],
}

DAYS = 90


def dirty_channel(channel):
    # ~3% of rows: a different export/vendor feed used lowercase channel names
    return channel.lower() if random.random() < 0.03 else channel


def generate_dataset(output_path="ga4_synthetic_adspend.csv", days=DAYS):
    start = datetime.utcnow().date() - timedelta(days=days)
    rows = []
    for d in range(days):
        event_date = (start + timedelta(days=d)).strftime("%Y%m%d")
        for channel in PAID_CHANNELS:
            for campaign in CAMPAIGNS_BY_CHANNEL[channel]:
                impressions = random.randint(500, 20000) if CHANNEL_CPC[channel] > 0 else random.randint(200, 5000)
                ctr = random.uniform(0.01, 0.06)
                clicks = max(0, int(impressions * ctr))
                cpc = CHANNEL_CPC[channel] * random.uniform(0.8, 1.3)
                spend = round(clicks * cpc, 2)

                # ~2% of rows: spend missing (vendor feed gap)
                if random.random() < 0.02:
                    spend = ""

                # ~1% of rows: negative spend (data entry / refund-adjustment error, unflagged)
                elif random.random() < 0.01:
                    spend = -abs(spend)

                rows.append({
                    "event_date": event_date,
                    "channel": dirty_channel(channel),
                    "campaign": campaign,
                    "impressions": impressions,
                    "clicks": clicks,
                    "spend": spend,
                    "currency": "USD",
                })

                # ~3% chance this exact row gets duplicated (vendor double-report on export)
                if random.random() < 0.03:
                    rows.append(dict(rows[-1]))

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["event_date", "channel", "campaign", "impressions", "clicks", "spend", "currency"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} ad spend rows across {days} days to {output_path}")


if __name__ == "__main__":
    generate_dataset()
