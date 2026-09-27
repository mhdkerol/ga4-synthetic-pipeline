"""
Regenerates ga4_synthetic_events with multi-session user journeys to support
multi-touch attribution modeling. Preserves the original schema shape and all
9 intentional data-quality issues from the v1 dataset.
"""
import json
import random
from datetime import datetime, timedelta

random.seed(42)
fake_first_names = None
try:
    from faker import Faker
    fake = Faker()
except ImportError:
    fake = None

START_DATE = datetime(2026, 6, 28)
END_DATE = datetime(2026, 9, 25)  # 90-day window, aligned with ad spend
TOTAL_DAYS = (END_DATE - START_DATE).days + 1
NUM_USERS = 2000

CHANNELS_FIRST = ["Direct", "Organic Search", "Paid Search", "Referral", "Social", "Email"]
CHANNELS_FIRST_W = [18, 18, 18, 16, 16, 14]
CHANNELS_RETURN = ["Direct", "Email", "Organic Search", "Paid Search", "Social", "Referral"]
CHANNELS_RETURN_W = [28, 26, 20, 14, 8, 4]

TOUCH_COUNT_CHOICES = [1, 2, 3, 4]
TOUCH_COUNT_W = [50, 30, 15, 5]

DEVICE_CATEGORIES = ["desktop", "mobile", "tablet"]
DEVICE_CATEGORY_W = [45, 48, 7]
OS_BY_CATEGORY = {
    "desktop": ["Windows", "Macintosh", "Linux"],
    "mobile": ["iOS", "Android"],
    "tablet": ["iOS", "Android"],
}
BROWSERS = ["Chrome", "Safari", "Edge", "Firefox"]

COUNTRIES = ["United States", "Canada", "United Kingdom", "Australia", "Germany", "Malaysia", "Singapore", "India"]
COUNTRY_W = [50, 10, 10, 8, 7, 6, 5, 4]
CITY_BY_COUNTRY = {
    "United States": ["New York", "Los Angeles", "Chicago", "Austin", "Seattle"],
    "Canada": ["Toronto", "Vancouver", "Montreal"],
    "United Kingdom": ["London", "Manchester"],
    "Australia": ["Sydney", "Melbourne"],
    "Germany": ["Berlin", "Munich"],
    "Malaysia": ["Kuala Lumpur", "Johor Bahru"],
    "Singapore": ["Singapore"],
    "India": ["Mumbai", "Bangalore"],
}

PRODUCTS = [
    ("SKU_001", "Wireless Earbuds", "Electronics", 49.99),
    ("SKU_002", "Yoga Mat", "Fitness", 29.99),
    ("SKU_003", "Stainless Water Bottle", "Fitness", 19.99),
    ("SKU_004", "Bluetooth Speaker", "Electronics", 39.99),
    ("SKU_005", "Running Shoes", "Apparel", 79.99),
    ("SKU_006", "Backpack", "Apparel", 59.99),
    ("SKU_007", "Desk Lamp", "Home", 24.99),
    ("SKU_008", "Coffee Grinder", "Home", 34.99),
]

FUNNEL = ["session_start", "page_view", "view_item", "add_to_cart",
          "begin_checkout", "add_shipping_info", "add_payment_info", "purchase"]


def sv(x):
    return {"string_value": x}


def iv(x):
    return {"int_value": x}


def dv(x):
    return {"double_value": x}


def weighted_choice(options, weights):
    return random.choices(options, weights=weights, k=1)[0]


def gen_device():
    cat = weighted_choice(DEVICE_CATEGORIES, DEVICE_CATEGORY_W)
    return {
        "category": cat,
        "operating_system": random.choice(OS_BY_CATEGORY[cat]),
        "web_info": {"browser": random.choice(BROWSERS)},
    }


def gen_geo(lowercase_bug):
    country = weighted_choice(COUNTRIES, COUNTRY_W)
    city = random.choice(CITY_BY_COUNTRY[country])
    if lowercase_bug:
        country = country.lower()
    return {"country": country, "city": city}


def gen_source_for_medium(medium):
    if medium == "Direct":
        return "(direct)"
    domain = fake.domain_name() if fake else "example.com"
    return domain


def user_pseudo_id(i, blank_bug):
    if blank_bug:
        return ""
    return f"u_{i:06d}_{random.randint(1000,9999)}"


def build_session_events(uid, session_id, session_number, session_dt, medium, source, device, geo,
                          reaches_purchase, discount_bug_window_start, blank_id_bug):
    events = []
    ts_cursor = session_dt
    product = random.choice(PRODUCTS)
    sku, name, cat, price = product
    qty = random.randint(1, 3)
    value = round(price * qty, 2)

    # decide how far this session's funnel goes
    if reaches_purchase:
        stage_names = FUNNEL
    else:
        # earlier browsing touch: stop somewhere between page_view and add_to_cart
        cutoff = random.choice(["page_view", "view_item", "add_to_cart"])
        stage_names = FUNNEL[:FUNNEL.index(cutoff) + 1]

    page_titles = {
        "session_start": "Home",
        "page_view": "Home",
        "view_item": name,
        "add_to_cart": "Cart",
        "begin_checkout": "Checkout",
        "add_shipping_info": "Checkout - Shipping",
        "add_payment_info": "Checkout - Payment",
        "purchase": "Order Confirmation",
    }

    currency_bug = random.random() < 0.05
    currency = "MYR" if currency_bug else "USD"

    for stage in stage_names:
        ts_cursor += timedelta(seconds=random.randint(15, 240))
        event_timestamp = int(ts_cursor.timestamp() * 1_000_000)
        event_date = ts_cursor.strftime("%Y%m%d")

        event_params = [
            {"key": "ga_session_id", "value": iv(session_id)},
            {"key": "ga_session_number", "value": iv(session_number)},
            {"key": "page_location", "value": sv(f"https://example-shop.com/{stage}")},
            {"key": "page_title", "value": sv(page_titles[stage])},
            {"key": "engagement_time_msec", "value": iv(random.randint(500, 60000))},
        ]
        if stage in ("add_to_cart", "begin_checkout", "add_shipping_info", "add_payment_info", "purchase"):
            event_params.append({"key": "value", "value": dv(value)})
            event_params.append({"key": "currency", "value": sv(currency)})

        # schema evolution bug: discount_code only in last 30 days, only on add_to_cart/purchase
        if stage in ("add_to_cart", "purchase") and ts_cursor >= discount_bug_window_start:
            if random.random() < 0.25:
                event_params.append({"key": "discount_code", "value": sv(random.choice(["SAVE10", "WELCOME15", "FALL20"]))})

        ecommerce = None
        items = []
        if stage in ("add_to_cart", "begin_checkout", "add_shipping_info", "add_payment_info", "purchase"):
            items = [{"item_id": sku, "item_name": name, "item_category": cat, "price": price}]
            ecommerce = {"transaction_id": f"T{session_id}" if stage == "purchase" else None,
                         "purchase_revenue": value if stage == "purchase" else None}
            if currency_bug and stage == "purchase":
                ecommerce["currency_note"] = "MYR"

        events.append({
            "event_date": event_date,
            "event_timestamp": event_timestamp,
            "event_name": stage,
            "user_pseudo_id": user_pseudo_id_value,
            "user_first_touch_timestamp": user_first_touch_ts,
            "device": device,
            "geo": geo,
            "traffic_source": {"medium": medium, "source": source},
            "event_params": event_params,
            "ecommerce": ecommerce,
            "items": items,
        })
    return events


all_events = []
discount_bug_window_start = END_DATE - timedelta(days=30)
session_counter = 1_000_000_000

for i in range(NUM_USERS):
    blank_id_bug = random.random() < 0.03
    user_pseudo_id_value = user_pseudo_id(i, blank_id_bug)

    touch_count = weighted_choice(TOUCH_COUNT_CHOICES, TOUCH_COUNT_W)
    # decide conversion: more touches -> higher chance of converting on final touch
    convert_prob = {1: 0.04, 2: 0.20, 3: 0.45, 4: 0.65}[touch_count]
    converts = random.random() < convert_prob

    # pick journey start day, leaving room for the touches + 30-day cap
    max_span_days = min(30, TOTAL_DAYS - 1)
    latest_start_offset = TOTAL_DAYS - 1 - (max_span_days if touch_count > 1 else 0)
    start_offset = random.randint(0, max(latest_start_offset, 0))
    journey_start = START_DATE + timedelta(days=start_offset)

    device = gen_device()
    lowercase_bug = random.random() < 0.05
    geo = gen_geo(lowercase_bug)

    user_first_touch_ts = int(journey_start.timestamp() * 1_000_000)

    touch_day_offsets = [0]
    for _ in range(touch_count - 1):
        gap = random.randint(1, 14)
        touch_day_offsets.append(touch_day_offsets[-1] + gap)
    # clip to window
    touch_day_offsets = [min(o, TOTAL_DAYS - 1 - start_offset) for o in touch_day_offsets]

    for t_idx, day_offset in enumerate(touch_day_offsets):
        session_dt = journey_start + timedelta(days=day_offset, hours=random.randint(6, 22), minutes=random.randint(0, 59))
        medium = weighted_choice(CHANNELS_FIRST, CHANNELS_FIRST_W) if t_idx == 0 else weighted_choice(CHANNELS_RETURN, CHANNELS_RETURN_W)
        source = gen_source_for_medium(medium)
        session_counter += 1
        is_last_touch = (t_idx == len(touch_day_offsets) - 1)
        reaches_purchase = converts and is_last_touch

        session_events = build_session_events(
            uid=i, session_id=session_counter, session_number=t_idx + 1, session_dt=session_dt,
            medium=medium, source=source, device=device, geo=geo,
            reaches_purchase=reaches_purchase,
            discount_bug_window_start=discount_bug_window_start,
            blank_id_bug=blank_id_bug,
        )
        all_events.extend(session_events)

        # ~2% duplicate-event bug: double-fire the session_start event
        if random.random() < 0.02 and session_events:
            all_events.append(dict(session_events[0]))

random.shuffle(all_events)
all_events.sort(key=lambda e: e["event_timestamp"])

out_path = "ga4_synthetic_events_v2.jsonl"
with open(out_path, "w") as f:
    for e in all_events:
        f.write(json.dumps(e) + "\n")

print(f"Wrote {len(all_events)} events to {out_path}")
print(f"Users: {NUM_USERS}")
