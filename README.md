# ga4-synthetic-pipeline

Multi-source marketing attribution modeling in dbt and BigQuery. Reconciles GA4-style event data and ad spend, which sit at different grains, into a star schema, models multi-touch attribution across user journeys, and (planned) defines metrics once in a dbt semantic layer.

> **Status: in progress.** Staging and intermediate layers are built and tested. Marts, semantic layer and dashboard are not built yet — see [Project Status](#project-status).

---

## ⚠️ Synthetic Data Disclosure

All data in this project is synthetic, generated with [Faker](https://faker.readthedocs.io/) and Python's standard library. My GA4 property has no collected traffic, so I generated event data **modeled on** the GA4 BigQuery export schema: nested `event_params`, `device`, `geo`, `traffic_source` and `ecommerce` records, with `ga_session_id` and `ga_session_number` as the session fields.

It is not a byte-for-byte replica of a real export and has not been validated against one. One deliberate simplification: in this dataset `traffic_source.medium` holds channel-group labels (e.g. "Paid Search", "Direct") instead of raw GA4 medium values like `cpc` or `organic`, so it joins to ad spend directly.

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
dbt Marts — Star Schema  (planned)
(dim_channel, dim_date, fact_sessions, fact_ad_spend, fact_attribution_credit)
        ↓
dbt Marts — Reporting Table  (planned)
(marketing_performance — flattened for BI)
        ↓
dbt MetricFlow Semantic Layer  (planned)
(ROAS, CAC, CTR defined once)
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
| Semantic Layer | dbt MetricFlow *(planned)* |
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
│   └── normalize_currency_to_usd.sql
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
│   └── marts/            (planned)
├── tests/
│   └── assert_credit_sums_to_one.sql
├── analyses/
├── seeds/
└── snapshots/
```

---

## Data Sources

**GA4 synthetic events** (`raw_ga4_events`) — ~2,000 users, 90-day window, full e-commerce funnel (`session_start` → `purchase`). Users have multi-session journeys (50% single-touch, 30% two-touch, 15% three-touch, 5% four-touch), so attribution credit can be split across real touchpoints rather than a single visit.

**Ad spend data** (`raw_ad_spend`) — daily spend, impressions and clicks by channel and campaign, same 90-day window. Channel names match the GA4 channel labels so the two sources join on channel and date.

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

The three core grains are different — session events, channel-day spend, and touchpoints within a conversion journey — so a star schema keeps each one honest. The reporting mart flattens everything to channel and day for the dashboard.

**Intermediate models (built):**

| Model | Grain |
|---|---|
| `int_sessions` | One row per session (`user_pseudo_id` + `ga_session_id`) |
| `int_channel_daily_spend` | One row per channel per day |
| `int_channel_daily_sessions` | One row per channel per day |
| `int_attribution_credit` | One row per conversion × touchpoint × attribution model |

**Facts (planned):** `fact_sessions`, `fact_ad_spend`, `fact_attribution_credit`
**Dimensions (planned):** `dim_channel` (union of channels from both sources), `dim_date`
**Reporting mart (planned):** `marketing_performance`

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

**30 dbt data tests across staging and intermediate.**

---

## Key Design Decisions

**Star schema + flattened reporting table.** Different grains need normalization to model correctly; the dashboard needs one flat table to avoid live joins.

**No ingestion or orchestration layer.** The pipeline starts from raw tables already in BigQuery, and the data is static — a scheduler for data that never changes adds nothing.

**Multi-touch attribution as the core modeling challenge**, built on journeys with genuine multi-session paths rather than single-visit data. Four models are kept side by side so they can be compared.

**Currency fix corrects the label, not the value.** I investigated the flagged issue before fixing it and confirmed the raw amount was never in a different currency, so the fix is a relabel, not a conversion.

**Fixed exchange rate in a dbt macro, no live FX API.** Consistent with the no-orchestration design.

**Conventions.** YAML tests live next to their models and use the `data_tests` key; cross-model checks are singular tests in `tests/`.

**Development approach.** Architecture and modeling decisions are mine. SQL and Python were written with AI assistance (Claude) and tested by me.

---

## Known Limitations

- Attribution runs on synthetic journeys, so it shows that the method works, not which channels perform.
- Channel values already match across the two sources by design, so `dim_channel` is a light conformance step; the harder problems are grain reconciliation and attribution.
- Direct has sessions but no ad spend, as expected. Organic Search has ad spend rows, which is a quirk of the generated data.
- Ad spend and staging dedupe use an `ORDER BY` on a column that is constant within each duplicate group, so which duplicate survives is arbitrary if duplicates differ.
- `users` in `int_channel_daily_sessions` is a distinct count per channel-day and is not additive across days.

---

## Project Status

- [x] Synthetic data generation (Faker)
- [x] BigQuery raw tables loaded
- [x] dbt project scaffolded and connected
- [x] Staging layer built and tested
- [x] Intermediate layer built and tested (including multi-touch attribution)
- [ ] Marts (star schema + reporting table)
- [ ] dbt MetricFlow semantic layer
- [ ] Power BI dashboard
- [ ] Architecture diagram + ERD

---

## Future Work

- Third data source (CRM / customer LTV) for lifetime-value attribution
- Product-level analysis using item-level event data
- Historical FX rate table as a more precise alternative to the fixed rate
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
```