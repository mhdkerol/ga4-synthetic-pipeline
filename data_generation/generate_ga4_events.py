"""
ga4-synthetic-pipeline
Synthetic GA4-shaped e-commerce event generator using Faker.

Mimics the schema of Google's real GA4 BigQuery export
(same structure as bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*):
nested event_params, device, geo, traffic_source, ecommerce, and items fields.

Output: newline-delimited JSON (NDJSON), one event per line — the format
BigQuery expects for GA4-style nested/repeated data.

Load it into BigQuery two ways, no coding required:
  A) BigQuery Console -> your dataset -> Create Table -> Upload -> select this
     .json file -> Format: JSONL (newline delimited) -> Auto-detect schema -> Create.
  B) CLI: bq load --source_format=NEWLINE_DELIMITED_JSON --autodetect \
          your_dataset.ga4_synthetic_events ga4_synthetic_events.json
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

DEVICE_CATEGORIES = ["desktop", "mobile", "tablet"]
OS_LIST = ["Windows", "iOS", "Android", "Macintosh", "Linux"]
BROWSERS = ["Chrome", "Safari", "Firefox", "Edge", "Samsung Internet"]
CHANNELS = ["Organic Search", "Direct", "Paid Search", "Referral", "Email", "Social"]
COUNTRIES = ["Malaysia", "Singapore", "United States", "Indonesia", "Australia", "India"]

PRODUCT_CATALOG = [
    {
        "item_id": f"SKU_{i:04d}",
        "item_name": fake.word().title() + " " + random.choice(
            ["Tee", "Mug", "Backpack", "Notebook", "Cap", "Hoodie"]
        ),
        "item_category": random.choice(["Apparel", "Accessories", "Office", "Bags"]),
        "price": round(random.uniform(5, 120), 2),
    }
    for i in range(1, 61)
]


def random_start_ts(start_days_ago=90):
    start = datetime.utcnow() - timedelta(days=start_days_ago)
    delta_seconds = random.randint(0, start_days_ago * 86400)
    return start + timedelta(seconds=delta_seconds)


def make_event_params(session_id, page_path, cart_items, event_name):
    params = [
        {"key": "session_id", "value": {"int_value": session_id}},
        {"key": "page_location", "value": {"string_value": f"https://ga4-synthetic-shop.example.com{page_path}"}},
        {"key": "page_title", "value": {"string_value": fake.catch_phrase()}},
        {"key": "engagement_time_msec", "value": {"int_value": random.randint(100, 60000)}},
    ]
    if event_name in ("view_item", "add_to_cart", "purchase") and cart_items:
        params.append({"key": "value", "value": {"double_value": round(sum(i["price"] for i in cart_items), 2)}})
        params.append({"key": "currency", "value": {"string_value": "USD"}})
    return params


def make_items(n=1):
    return random.sample(PRODUCT_CATALOG, k=min(n, len(PRODUCT_CATALOG)))


def generate_user_session(user_pseudo_id):
    events = []
    ts = random_start_ts()
    session_id = random.randint(1_000_000_000, 9_999_999_999)
    device = random.choice(DEVICE_CATEGORIES)
    os_name = random.choice(OS_LIST)
    browser = random.choice(BROWSERS)
    channel = random.choice(CHANNELS)
    country = random.choice(COUNTRIES)

    # Deliberate messiness: ~3% of sessions arrive with a blank user_pseudo_id
    # (simulates consent/late-binding gaps you'd actually see in real GA4 exports)
    effective_user_id = "" if random.random() < 0.03 else user_pseudo_id

    funnel = ["session_start", "page_view"]
    cart_items = []
    if random.random() < 0.55:
        funnel.append("view_item")
        cart_items = make_items(random.randint(1, 3))
        if random.random() < 0.35:
            funnel.append("add_to_cart")
            if random.random() < 0.5:
                funnel += ["begin_checkout", "add_shipping_info", "add_payment_info"]
                if random.random() < 0.7:
                    funnel.append("purchase")

    for i, event_name in enumerate(funnel):
        event_ts = ts + timedelta(seconds=i * random.randint(5, 90))
        ecommerce = None
        if event_name in ("purchase", "add_to_cart", "view_item"):
            ecommerce = {
                "purchase_revenue": round(sum(it["price"] for it in cart_items), 2) if event_name == "purchase" else None
            }
        record = {
            "event_date": event_ts.strftime("%Y%m%d"),
            "event_timestamp": int(event_ts.timestamp() * 1_000_000),
            "event_name": event_name,
            "event_params": make_event_params(session_id, f"/{fake.uri_path()}", cart_items, event_name),
            "user_pseudo_id": effective_user_id,
            "user_first_touch_timestamp": int((ts - timedelta(days=random.randint(0, 60))).timestamp() * 1_000_000),
            "device": {
                "category": device,
                "operating_system": os_name,
                "web_info": {"browser": browser},
            },
            "geo": {"country": country, "city": fake.city()},
            "traffic_source": {
                "medium": channel,
                "source": (fake.domain_word() + ".com") if channel != "Direct" else "(direct)",
            },
            "ecommerce": ecommerce,
            "items": cart_items if event_name in ("view_item", "add_to_cart", "purchase") else [],
        }
        events.append(record)
    return events


def dirty_country(country):
    # ~5% of rows: inconsistent casing, mimicking a client-side/library change mid-stream
    return country.lower() if random.random() < 0.05 else country


def apply_currency_drift(event):
    # ~5% of purchase/ecommerce events report in MYR instead of USD, value NOT converted
    # (a very real "someone changed a config and nobody normalized historical data" bug)
    if event["event_name"] == "purchase" and random.random() < 0.05:
        for p in event["event_params"]:
            if p["key"] == "currency":
                p["value"]["string_value"] = "MYR"
        if event.get("ecommerce"):
            event["ecommerce"]["currency_note"] = "MYR"  # left unconverted on purpose
    return event


def apply_schema_evolution(event, event_ts, cutoff_date):
    # In the most recent ~30 days, a new event_param key was added upstream —
    # older events simply don't have it (classic schema-evolution scenario)
    if event_ts.date() >= cutoff_date and event["event_name"] in ("add_to_cart", "purchase"):
        if random.random() < 0.4:
            event["event_params"].append({"key": "discount_code", "value": {"string_value": random.choice(["WELCOME10", "SAVE15", ""])}})
    return event


def maybe_duplicate(events):
    # ~2% chance a session has one event double-fired (classic tracking pixel bug),
    # appended as a near-identical duplicate a few seconds later
    if events and random.random() < 0.02:
        dup = json.loads(json.dumps(random.choice(events)))
        dup["event_timestamp"] += random.randint(1, 3) * 1_000_000
        events.append(dup)
    return events


def generate_dataset(n_users=2000, output_path="ga4_synthetic_events.json"):
    total_events = 0
    cutoff_date = (datetime.utcnow() - timedelta(days=30)).date()
    with open(output_path, "w") as f:
        for _ in range(n_users):
            user_id = str(uuid.uuid4())
            events = generate_user_session(user_id)
            events = maybe_duplicate(events)
            for event in events:
                event_ts = datetime.utcfromtimestamp(event["event_timestamp"] / 1_000_000)
                event["geo"]["country"] = dirty_country(event["geo"]["country"])
                event = apply_currency_drift(event)
                event = apply_schema_evolution(event, event_ts, cutoff_date)
                f.write(json.dumps(event) + "\n")
                total_events += 1
    print(f"Wrote {total_events} synthetic GA4 events for {n_users} users to {output_path}")


if __name__ == "__main__":
    generate_dataset(n_users=2000, output_path="ga4_synthetic_events.json")
