# ga4-synthetic-pipeline

Multi-source marketing attribution modeling in dbt and BigQuery. Reconciles GA4-style event data and ad spend, which sit at different grains, into a star schema, models multi-touch attribution across user journeys, and defines marketing metrics (ROAS, cost per click, click-through rate and more) once in a dbt MetricFlow semantic layer.

> **Status: in progress.** Staging, intermediate, marts and the semantic layer are built and tested. The Power BI dashboard is not built yet — see [Project Status](#project-status).

---

## ⚠️ Synthetic Data Disclosure

All data in this project is synthetic, generated with [Faker](https://faker.readthedocs.io/) and Python's standard library. My GA4 account has no website linked to it, so there is no real traffic to export. I generated event data **modeled on** the GA4 BigQuery export schema: nested `event_params`, `device`, `geo`, `traffic_source` and `ecommerce` records, with `ga_session_id` and `ga_session_number` as the session fields.

Google's public GA4 sample dataset was not used because it contains events only. This project is about reconciling two sources at different grains (events and ad spend), so it needed a matching ad spend source, and generating both let me inject known data quality problems and prove the cleaning works.

The data is not a byte-for-byte replica of a real export and has not been validated against one. One deliberate simplification: `traffic_source.medium` holds channel-group labels (e.g. "Paid Search", "Direct") instead of raw GA4 medium values like `cpc` or `organic`, so it joins to ad spend directly.

Only the underlying data is fabricated. The pipeline, modeling and tests on top of it are real, but **attribution results on synthetic data demonstrate the method, not real channel performance.**

---

## Architecture Flow

```
Faker Synthetic Generators
(data_generation/generate_ga4_events.py, generate_adspend.py)
        ↓
BigQuery raw tables — ga4_synthetic_raw dataset (manual upload)
(raw_ga4_events, raw_ad_spend)
        ↓
dbt Staging  ✅
(unnest event_params, dedupe, normalize casing/currency)
        ↓
dbt Intermediate  ✅
(int_sessions, int_channel_daily_spend, int_channel_daily_sessions, int_attribution_credit)
        ↓
dbt Marts — Star Schema  ✅
(dim_channel, dim_date, fact_sessions, fact_ad_spend, fact_attribution_credit)
        ↓
dbt Marts — Reporting Table  ✅
(marketing_performance — one row per channel per day, flattened for BI)
        ↓
dbt MetricFlow Semantic Layer  ✅
(10 simple + 8 ratio metrics: ROAS, cost per click, CTR, conversion rate, cost per purchase)
        ↓
Power BI Dashboard  (planned)
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Synthetic Data Generation | Python 3.13, Faker |
| Warehouse | BigQuery |
| Transformation | dbt-core 1.12, dbt-bigquery 1.12 |
| Testing | dbt data tests, singular tests, `dbt_utils` |
| Semantic Layer | dbt MetricFlow (`dbt-metricflow` 0.15, run locally with the `mf` CLI) |
| Dashboard | Power BI *(planned)* |

---

## Project Structure

```
ga4-synthetic-pipeline/
├── .gitignore
├── dbt_project.yml
├── packages.yml
├── package-lock.yml
├── requirements.txt
├── README.md
├── data_generation/
│   ├── generate_ga4_events.py
│   ├── generate_adspend.py
│   ├── ga4_synthetic_events_v2.jsonl
│   └── ga4_synthetic_adspend.csv
├── macros/
│   └── label_currency_as_usd.sql
├── models/
│   ├── staging/
│   │   ├── sources.yml
│   │   ├── stg_ga4_events.sql / .yml
│   │   └── stg_ad_spend.sql / .yml
│   ├── intermediate/
│   │   ├── int_sessions.sql / .yml
│   │   ├── int_channel_daily_spend.sql
│   │   ├── int_channel_daily_sessions.sql
│   │   ├── int_channel_daily.yml
│   │   ├── int_attribution_credit.sql
│   │   └── int_attribution_credit.yml
│   └── marts/
│       ├── dim_channel.sql / .yml
│       ├── dim_date.sql / .yml
│       ├── fact_sessions.sql / .yml
│       ├── fact_ad_spend.sql / .yml
│       ├── fact_attribution_credit.sql / .yml
│       └── marketing_performance.sql / .yml   (also holds the semantic model and metrics)
├── tests/                                      (singular tests: credit sums, fact-vs-source reconciliation)
├── analyses/
├── seeds/
└── snapshots/
```

---

## Data Sources

**GA4 synthetic events** (`raw_ga4_events`) — ~2,000 users, 90-day window (2026-06-28 to 2026-09-25), full e-commerce funnel (`session_start` → `purchase`). Users have multi-session journeys (50% single-touch, 30% two-touch, 15% three-touch, 5% four-touch), so attribution credit can be split across real touchpoints rather than a single visit.

**Ad spend data** (`raw_ad_spend`) — daily spend, impressions and clicks by channel and campaign, same 90-day window (checked: both sources cover the same 90 days). Channel names match the GA4 channel labels so the two sources join on channel and date.

| Dataset | Purpose |
|---|---|
| `ga4_synthetic_raw` | Raw tables: `raw_ga4_events`, `raw_ad_spend` |
| `ga4_synthetic_dbt` | dbt-built staging / intermediate / marts models |

### Loading raw data

The two files in `data_generation/` are uploaded to BigQuery manually through the console. There is no ingestion layer by design, since the data is static.

| File | BigQuery table |
|---|---|
| `ga4_synthetic_events_v2.jsonl` | `ga4_synthetic_raw.raw_ga4_events` |
| `ga4_synthetic_adspend.csv` | `ga4_synthetic_raw.raw_ad_spend` |

---

## Data Model

The three core grains are different — session events, channel-day spend, and touchpoints within a conversion journey — so a star schema keeps each one honest. The reporting table then flattens everything to channel and day for the dashboard.

**Intermediate models:**

| Model | Grain |
|---|---|
| `int_sessions` | One row per session (`user_pseudo_id` + `ga_session_id`) |
| `int_channel_daily_spend` | One row per channel per day |
| `int_channel_daily_sessions` | One row per channel per day |
| `int_attribution_credit` | One row per conversion × touchpoint × attribution model |

**Marts:**

| Model | Type | Grain | Built from |
|---|---|---|---|
| `dim_channel` | Dimension | One row per channel (6) | Distinct channels from both channel-day intermediates; adds `channel_type` (Paid / Unpaid) |
| `dim_date` | Dimension | One row per day (90) | Date range found across both sources; also the MetricFlow time spine |
| `fact_sessions` | Fact | One row per session (3,429) | `int_sessions` + `dim_channel` key |
| `fact_ad_spend` | Fact | One row per channel per day (450) | `int_channel_daily_spend` + `dim_channel` key |
| `fact_attribution_credit` | Fact | One row per credited touchpoint per attribution model | `int_attribution_credit` + `dim_channel` key |
| `marketing_performance` | Reporting table | One row per channel per day (540) | The three facts and two dimensions above |

Every fact is checked against its source by a singular test (same row count, same totals), so a join cannot silently lose or duplicate rows.

---

## Multi-Touch Attribution

`int_attribution_credit` treats each purchasing session as a conversion. A conversion's journey is every session by that user up to and including the purchasing session, ordered by session start time. Credit is then distributed four ways, and credit sums to 1.0 per conversion per model (enforced by a singular test):

| Model | Rule |
|---|---|
| First touch | 100% to the first session |
| Last touch | 100% to the last session |
| Linear | Equal share to every session |
| Position-based (U-shaped) | 40% first, 40% last, 20% split across the middle; a one-touch journey gets 100%, a two-touch journey gets 50/50 |

Assumptions: no lookback window (a journey is the user's full history), Direct is treated like any other channel, and a user with several purchases has overlapping journeys.

**Revenue by channel and model (synthetic data — illustrates method only; every model totals $29,428.20 across 338 conversions):**

| Channel | First touch | Last touch | Linear | Position-based |
|---|---|---|---|---|
| Direct | 5,268.84 | 7,863.25 | 6,994.23 | 6,806.47 |
| Email | 4,249.04 | 7,373.23 | 6,340.66 | 6,050.61 |
| Organic Search | 4,848.90 | 5,583.79 | 5,487.13 | 5,401.31 |
| Paid Search | 7,318.39 | 4,978.90 | 5,433.37 | 5,744.72 |
| Referral | 4,438.90 | 1,569.59 | 2,704.32 | 2,850.29 |
| Social | 3,304.13 | 2,059.44 | 2,468.50 | 2,574.81 |

Half of all users have a single touch, so all four models give them identical credit. The models can only differ on multi-touch journeys.

---

## Semantic Layer (dbt MetricFlow)

Metrics are defined once, in `models/marts/marketing_performance.yml`, on top of the `marketing_performance` table. MetricFlow adds numbers up first and divides afterwards, so a ratio is correct at any grouping (by channel, channel type, month, weekday).

| Type | Metrics |
|---|---|
| Simple (10) | `total_spend`, `total_impressions`, `total_clicks`, `total_sessions`, `total_purchasing_sessions`, `total_purchase_revenue`, `first_touch_revenue`, `last_touch_revenue`, `linear_revenue`, `position_based_revenue` |
| Ratio (8) | `roas_first_touch`, `roas_last_touch`, `roas_linear`, `roas_position_based`, `cost_per_click`, `click_through_rate`, `session_conversion_rate`, `cost_per_purchase` |

Group-by dimensions: `channel_name`, `channel_type`, `month_name`, `day_of_week_name` and time (`metric_time`).

`mf validate-configs` passes with no errors, including the checks against BigQuery, and `mf query` totals match the warehouse (spend 186,249.58; revenue 29,428.20; 3,429 sessions).

---

## Data Quality Issues Handled

| Issue | Rate | Fix |
|---|---|---|
| Blank `user_pseudo_id` | ~3% | Converted to `NULL` in staging; those sessions are then excluded from `int_sessions` because they can't be tied to a journey (~108 sessions, including 9 of 347 purchases) |
| Duplicate double-fired events | ~2% | Deduped via `ROW_NUMBER()`, verified with a uniqueness test |
| Lowercase `geo.country` | ~5% | `INITCAP()` |
| Currency label mismatch (5% of purchases tagged MYR) | ~5% | Corrected the label to USD without rescaling the value — the underlying amount was never actually in MYR terms, so dividing by an exchange rate would have introduced a distortion rather than fixing one |
| `discount_code` present only in last 30 days | last 30d | Left `NULL` for older events — schema evolution, not backfilled |
| Ad spend duplicate rows | ~3% | Deduped via `ROW_NUMBER()` |
| Ad spend missing `spend` | ~2% | Left `NULL` — aggregations skip nulls |
| Ad spend negative `spend` | ~1% | Nulled as invalid |
| Ad spend lowercase channel | ~3% | `INITCAP()` |

**79 dbt data tests** across all layers, including singular tests that reconcile each fact and the reporting table against their sources.

---

## Key Design Decisions

**Star schema + flattened reporting table.** Different grains need normalization to model correctly; the dashboard needs one flat table to avoid live joins.

**No ingestion or orchestration layer.** The pipeline starts from raw tables already in BigQuery, and the data is static — a scheduler for data that never changes adds nothing.

**Multi-touch attribution as the core modeling challenge**, built on journeys with genuine multi-session paths rather than single-visit data. Four models are kept side by side so they can be compared.

**Currency fix corrects the label, not the value.** I investigated the flagged issue before fixing it and confirmed the raw amount was never in a different currency, so the fix is a relabel, not a conversion. The macro is named `label_currency_as_usd` so its name says what it does.

**`channel_type` is a manual two-value mapping (Paid / Unpaid) in `dim_channel`.** Paid Search and Social are Paid. Email is Unpaid because the contact list is already owned and the only cost is operational (sending), not buying traffic. The mapping lives in the warehouse so every downstream tool gets the same answer. A channel outside the list becomes `Unmapped` and fails the accepted-values test, so a new channel cannot be silently mislabeled.

**Device and country stay as plain columns on `fact_sessions`, with no `dim_device` or `dim_geo`.** In this synthetic data, device and country are random and have no effect on conversion, so a dimension would suggest insight that isn't there. There is also no timezone data to support a campaign-timing analysis.

**`fact_ad_spend` is at channel-day grain, not campaign grain.** Sessions don't carry a campaign, so channel-day is the only level at which spend and sessions can be compared.

**Attributed revenue lands on the touch day, not the purchase day.** `fact_attribution_credit` keeps only `touch_date`. That is the right day for comparing a channel with its spend; the cost is that attributed revenue can appear earlier than the purchase itself.

**`marketing_performance` has one row per channel per day, with the four attribution models as four columns, not four rows.** With four rows per day, spend would repeat on each and a chart summing it would show four times the real number. The table is built from a channel × day spine (6 × 90 = 540 rows) and every source is brought to channel-day grain before joining, so Direct (no spend rows) and quiet days are not lost and no join can multiply rows. Sessions and revenue default to 0 when nothing happened; `spend` stays `NULL` where there is no spend or the source value was missing.

**No ratios stored in any table.** ROAS, cost per click and click-through rate cannot be averaged across rows (a $10 day would count as much as a $1,000 day). They are defined once in MetricFlow and calculated from summed totals.

**One semantic model, on `marketing_performance` only.** The reporting table is already at a single grain, so there is nothing to join, which avoids a class of mistakes. The trade-off is that it shows less of MetricFlow's join capability.

**`cost_per_purchase` instead of CAC.** CAC means cost per *new* customer, and the data has no new-versus-returning customer information. `cost_per_purchase` (spend ÷ purchasing sessions) is what the data supports.

**`dim_date` doubles as the MetricFlow time spine.** It already has one row per day, so a separate spine table isn't needed.

**Conventions.** YAML tests live next to their models and use the `data_tests` key; cross-model checks are singular tests in `tests/`.

**Development approach.** I designed the architecture, chose every grain and modeling decision, and tested and verified the results (reconciling each model against its source). SQL and Python were written with AI assistance (Claude).

---

## Known Limitations

- Attribution runs on synthetic journeys, so it shows that the method works, not which channels perform.
- Channel values already match across the two sources by design, so `dim_channel` is a light conformance step; the harder problems are grain reconciliation and attribution.
- Direct has sessions but no ad spend, as expected, so all of its spend-based metrics come back empty, not zero. Organic Search and Referral have ad spend rows with zero cost, which is a quirk of the generated data: their ROAS is empty (division by zero) and their cost per click is 0.
- 94 of the 540 channel-day rows have empty `spend`: 90 are Direct (no spend rows) and 4 are channel-days where every campaign's spend was missing or invalid. Totals for those days are slightly understated.
- Attributed revenue is counted on the touch day, so it does not line up day by day with purchase revenue (the totals do match).
- Ad spend and staging dedupe use an `ORDER BY` on a column that is constant within each duplicate group, so which duplicate survives is arbitrary if duplicates differ. In this data the duplicates are identical, so it makes no difference.
- `users` in `int_channel_daily_sessions` is a distinct count per channel-day and is not additive across days.

---

## Project Status

- [x] Synthetic data generation (Faker)
- [x] BigQuery raw tables loaded
- [x] dbt project scaffolded and connected
- [x] Staging layer built and tested
- [x] Intermediate layer built and tested (including multi-touch attribution)
- [x] Marts built and tested (star schema + reporting table)
- [x] dbt MetricFlow semantic layer (10 simple + 8 ratio metrics, validated)
- [ ] Power BI dashboard
- [ ] Architecture diagram + ERD

---

## Future Work

What I would add with real data:
- `dim_device` (operating system, browser) to show which devices engage and convert, for UI/UX decisions
- `dim_geo` with timezone, to time campaigns for visitors in different regions
- Customer-level data (new vs returning) so `cost_per_purchase` can become a true CAC

Other ideas:
- Third data source (CRM / customer LTV) for lifetime-value attribution
- Product-level analysis using item-level event data
- Lookback windows for attribution

---

## Setup

```
git clone https://github.com/mhdkerol/ga4-synthetic-pipeline.git
cd ga4-synthetic-pipeline

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# optional — data is already committed; the generators are seeded and deterministic
python data_generation/generate_ga4_events.py
python data_generation/generate_adspend.py

# dbt (requires your own BigQuery project and a profiles.yml, which is not in the repo)
dbt deps
dbt debug
dbt build

# semantic layer (the mf command looks for profiles.yml in the folder set by DBT_PROFILES_DIR)
$env:DBT_PROFILES_DIR = "$HOME\.dbt"
mf validate-configs
mf list metrics
mf query --metrics total_spend,roas_last_touch --group-by marketing_performance__channel_name
```