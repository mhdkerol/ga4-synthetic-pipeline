# ga4-synthetic-pipeline

A multi-source marketing attribution pipeline built on synthetic GA4 e-commerce event data and ad spend data, using dbt and BigQuery. Blends two sources with mismatched schemas into a conformed star schema, models multi-touch attribution across user journeys, and defines metrics once through a dbt semantic layer.

> **Status: in progress.** Staging layer complete and tested (14/14 dbt tests passing). Intermediate, marts, semantic layer, and dashboard are not yet built — see [Project Status](#project-status).

---

## ⚠️ Synthetic Data Disclosure

All data in this project is synthetic, generated with [Faker](https://faker.readthedocs.io/). My GA4 property has no collected traffic, so event data was generated to match GA4's real BigQuery export schema exactly — nested `event_params`, `device`, `geo`, `traffic_source`, `ecommerce`, `items` — verified against Google's official export documentation. Only the underlying event data is fabricated; the pipeline and modeling on top of it are real.

---

## Architecture Flow

```
Faker Synthetic Generators
(data_generation/generate_ga4_events.py, generate_ad_spend.py)
        ↓
BigQuery raw tables — ga4_synthetic_raw dataset
(raw_ga4_events, raw_ad_spend)
        ↓
dbt Staging
(unnest event_params, dedupe, normalize casing/currency)
        ↓
dbt Intermediate
(int_sessions, int_channel_daily_spend, int_channel_daily_sessions, int_attribution_credit)
        ↓
dbt Marts — Star Schema
(dim_channel, dim_date, fact_sessions, fact_ad_spend, fact_attribution_credit)
        ↓
dbt Marts — Reporting Table
(marketing_performance — flattened, pre-aggregated)
        ↓
dbt MetricFlow Semantic Layer
(ROAS, CAC, CTR defined once)
        ↓
Power BI Dashboard
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Synthetic Data Generation | Python 3.13, Faker |
| Warehouse | BigQuery |
| Transformation | dbt-bigquery 1.12 |
| Testing | dbt tests + `dbt_utils` |
| Semantic Layer | dbt MetricFlow *(planned)* |
| Dashboard | Power BI *(planned)* |

---

## Project Structure

```
ga4-synthetic-pipeline/
├── .gitignore
├── dbt_project.yml
├── packages.yml
├── README.md
├── data_generation/
│   ├── generate_ga4_events.py
│   ├── generate_ad_spend.py
│   ├── ga4_synthetic_events_v2.jsonl
│   └── ga4_synthetic_adspend.csv
├── macros/
│   └── normalize_currency_to_usd.sql
├── models/
│   ├── staging/
│   │   ├── sources.yml
│   │   ├── stg_ga4_events.sql
│   │   ├── stg_ga4_events.yml
│   │   ├── stg_ad_spend.sql
│   │   └── stg_ad_spend.yml
│   ├── intermediate/
│   └── marts/
├── seeds/
└── tests/
```

---

## Data Sources

**GA4 synthetic events** (`raw_ga4_events`) — ~2,000 users, 90-day window, full e-commerce funnel (session_start → purchase). Users have genuine multi-session journeys (50% single-touch, 30% two-touch, 15% three-touch, 5% four-touch), so attribution credit can be split across real touchpoints rather than a single visit.

**Ad spend data** (`raw_ad_spend`) — daily spend/impressions/clicks by channel and campaign, same 90-day window, channels aligned to GA4's `traffic_source.medium` for a clean join.

| Dataset | Purpose |
|---|---|
| `ga4_synthetic_raw` | Raw tables: `raw_ga4_events`, `raw_ad_spend` |
| `ga4_synthetic_dbt` | dbt-built staging/intermediate/marts models |

---

## Data Model

Star schema core, feeding a flattened reporting table. Session-level events, channel-day-level spend, and touchpoint-in-journey attribution are three different grains — a star schema keeps each honest, and the reporting mart flattens everything to channel+day for the dashboard layer.

**Fact Tables (planned):**

| Model | Grain |
|---|---|
| `fact_sessions` | One row per session |
| `fact_ad_spend` | One row per channel/campaign/day |
| `fact_attribution_credit` | One row per session within a converting journey |

**Dimension Tables (planned):**

| Model | Description |
|---|---|
| `dim_channel` | Conforms GA4's `traffic_source.medium` and ad spend's `channel` into one value |
| `dim_date` | Standard date dimension |

---

## Data Quality Issues Handled

| Issue | Rate | Fix |
|---|---|---|
| Blank `user_pseudo_id` | ~3% | Converted to `NULL` |
| Duplicate double-fired events | ~2% | Deduped via `ROW_NUMBER()`, verified with a uniqueness test |
| Lowercase `geo.country` | ~5% | `INITCAP()` |
| Currency label mismatch (5% of purchases tagged MYR) | ~5% | Corrected the label to USD without rescaling the value — the underlying amount was never actually in MYR terms, so dividing by an exchange rate would have introduced a real distortion rather than fixing one |
| `discount_code` present only in last 30 days | last 30d | Left `NULL` for older events — schema evolution, not backfilled |
| Ad spend duplicate rows | ~3% | Deduped via `ROW_NUMBER()` |
| Ad spend missing `spend` | ~2% | Left `NULL` — aggregations skip nulls automatically |
| Ad spend negative `spend` | ~1% | Nulled as invalid |
| Ad spend lowercase channel | ~3% | `INITCAP()` |

**14/14 dbt tests passing on the staging layer.**

---

## Key Design Decisions

**Star schema + flattened reporting table.** Different grains (sessions, channel-days, attribution touchpoints) need normalization to model correctly; the dashboard needs one flat table to avoid live joins.

**No ingestion or orchestration layer.** The pipeline starts from raw tables already in BigQuery, and the data is static — a scheduler for data that never changes adds nothing.

**Multi-touch attribution as the core modeling challenge**, built on user journeys with genuine multi-session paths rather than single-visit data.

**Currency fix corrects the label, not the value.** Investigated the flagged issue before fixing it — confirmed the raw amount was never actually in a different currency, so the fix is a relabel, not a conversion.

**Fixed exchange rate, no live FX API.** Consistent with the no-orchestration design — a live pull would add scheduling complexity for a static dataset.

---

## Project Status

- [x] Synthetic data generation (Faker)
- [x] BigQuery raw tables loaded
- [x] dbt project scaffolded and connected
- [x] Staging layer built and tested (14/14 passing)
- [ ] Intermediate layer
- [ ] Marts (star schema + reporting table)
- [ ] dbt MetricFlow semantic layer
- [ ] Power BI dashboard
- [ ] Architecture diagram + ERD

---

## Future Work

- Third data source (CRM/customer LTV) for lifetime-value attribution
- Product-level detail via GA4's existing `items[]` array
- Historical FX rate table as a more precise alternative to the fixed rate

---

## Setup

```
git clone https://github.com/mhdkerol/ga4-synthetic-pipeline.git
cd ga4-synthetic-pipeline

# optional — data is already committed; both generators are seeded and deterministic
pip install faker
python data_generation/generate_ga4_events.py
python data_generation/generate_ad_spend.py

# dbt
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install dbt-core dbt-bigquery
dbt deps
dbt debug
dbt run --select staging
dbt test --select staging
```