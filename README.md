# YouTube Analytics Engineering Pipeline

An end-to-end analytics engineering project that ingests YouTube data using the YouTube Data API v3, stores raw data in Google Cloud Storage, transforms it with dbt following the medallion architecture (ELT pattern), and automates the full pipeline with GitHub Actions. Built to demonstrate core AE skills in pipeline design, dimensional modelling, data quality, and documentation using a real-world marketing analytics use case.

---

## Architecture Diagram

![Architecture Diagram](docs/architecture.png)

---

## Data Lineage

![dbt Lineage Graph](docs/lineage.png)

> Generated with `dbt docs generate`. Lineage covers the full pipeline from YouTube API sources through silver staging models to the gold star schema, with the Looker Studio dashboard as the downstream exposure. `fct_searches` and `fct_comments` are fully built and tested but not connected to the dashboard — included as complete deliverables demonstrating the full data model.

---

## dbt Documentation

![dbt Docs Site](docs/dbt_docs.png)

All models, columns, and tests are fully documented in dbt. Descriptions cover grain, business logic, known data anomalies (e.g. `engagement_rate > 1` from external embeds), SCD Type 2 behaviour on `dim_channels`, and `rank_change` interpretation in `fct_searches`.

---

## Dashboard

**YouTube Analytics Dashboard** — [View Live](https://datastudio.google.com/reporting/b1613135-f59a-499a-954f-48be1660cb7e/page/0UbvF)

![Dashboard](docs/dashboard.png)

Built in Looker Studio on top of the gold layer star schema. Three pages covering market landscape, video performance drivers, and channel intelligence. The dashboard serves as a consumption layer to validate the pipeline output is accurate and queryable. Primary engineering work is in the dbt transformation layer.

---

## Architecture Flow

```
YouTube Data API v3
        ↓
Python Ingestion Script
        ↓
Google Cloud Storage — Bronze Layer
gs://bucket/bronze/youtube/{endpoint}/YYYY/MM/DD/
        ↓
BigQuery Bronze Tables
(append only, day partitioned, duplicate check)
        ↓
dbt Source Freshness Check
        ↓
dbt Silver Layer
(cast, deduplicate, filter nulls, rename)
        ↓
dbt Snapshot — SCD Type 2
(channel history tracking)
        ↓
dbt Gold Layer
(star schema, business metrics)
        ↓
Looker Studio Dashboard
GitHub Actions — orchestrates & automates the full pipeline
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Language | Python 3.11 |
| Ingestion | `google-api-python-client` |
| Secrets | `python-dotenv` + `.env` |
| IDE | VS Code |
| Raw Storage | Google Cloud Storage (GCS) |
| Warehouse | BigQuery (`yt-ae-project`) |
| Transformation | dbt-bigquery 1.11.1 |
| Documentation | dbt docs (models, columns, lineage, exposures) |
| Data Quality | dbt tests + source freshness checks |
| Orchestration | GitHub Actions (automated weekly) |
| Version Control | Git + GitHub |
| Dashboard | Looker Studio |

---

## Project Structure

```
youtube-analytics-API/
├── .env                              ← secrets (never committed)
├── .env.example                      ← env template
├── .gitignore
├── requirements.txt
├── docs/
│   ├── architecture.png              ← architecture diagram
│   ├── erd.png                       ← entity relationship diagram
│   ├── lineage.png                   ← dbt lineage graph
│   ├── dbt_docs.png                  ← dbt docs site screenshot
│   └── dashboard.png                 ← Looker Studio screenshot
├── .github/
│   └── workflows/
│       └── youtube_pipeline.yml      ← GitHub Actions pipeline
├── ingestion/
│   ├── youtube_ingestion.py          ← YouTube API → GCS
│   └── load_gcs_to_bigquery.py       ← GCS → BigQuery
└── transformation/
    └── youtube_analytics/            ← dbt project root
        ├── dbt_project.yml
        ├── packages.yml              ← dbt_utils
        ├── macros/
        │   └── generate_schema_name.sql
        ├── models/
        │   ├── exposures.yml         ← Looker Studio dashboard exposure
        │   ├── silver/
        │   │   ├── sources.yml       ← source definitions + freshness config
        │   │   ├── schema.yml        ← silver model + column descriptions + tests
        │   │   ├── stg_youtube_videos.sql
        │   │   ├── stg_youtube_channels.sql
        │   │   ├── stg_youtube_comments.sql
        │   │   ├── stg_youtube_searches.sql
        │   │   └── stg_youtube_categories.sql
        │   └── gold/
        │       ├── schema.yml        ← gold model + column descriptions + tests + relationships
        │       ├── dim_dates.sql
        │       ├── dim_channels.sql
        │       ├── dim_categories.sql
        │       ├── fct_video_performance.sql
        │       ├── fct_comments.sql
        │       └── fct_searches.sql
        └── snapshots/
            └── snp_youtube_channels.sql
```

---

## Data Sources

All data is pulled from the **YouTube Data API v3** across 5 endpoints:

| Endpoint | Data |
|---|---|
| Search | Video IDs by keyword, search rank, retrieved timestamp |
| Videos | Stats, duration, tags, category, caption, definition |
| Channels | Subscribers, views, country, topics, keywords |
| Comments | Comment text, likes, reply count, author |
| Video Categories | Category ID to name mapping |

### Search Keywords (Marketing Theme)

```python
KEYWORDS = [
    "digital marketing tutorial",
    "social media strategy",
    "seo tips 2025",
    "content marketing",
    "email marketing",
    "google ads tutorial",
    "influencer marketing",
    "youtube growth tips",
    "brand strategy",
    "marketing analytics",
    "digital marketing for beginners",
    "how to start digital marketing",
    "online marketing tutorial",
    "how to grow on youtube",
    "youtube algorithm explained",
    "youtube seo tips",
    "youtube thumbnail tips",
    "youtube content strategy",
    "instagram marketing strategy",
    "tiktok marketing tips",
    "facebook ads tutorial",
    "how to go viral on youtube",
    "how to get more views",
    "how to increase engagement",
    "content creation tips",
    "short form video strategy",
    "youtube shorts growth",
    "ai marketing tools",
    "chatgpt for marketing",
    "keyword research tutorial"
]
```

---

## Data Model

### BigQuery Datasets

| Dataset | Purpose |
|---|---|
| `youtube_bronze` | Raw tables from GCS, append only, day partitioned |
| `youtube_silver` | dbt staging models: clean, typed, deduplicated |
| `snapshots` | SCD Type 2 channel history |
| `youtube_gold` | dbt mart models: star schema, business metrics |

### Entity Relationship Diagram

![ERD](docs/erd.png)

Star schema with three fact tables (`fct_video_performance`, `fct_comments`, `fct_searches`) and three dimension tables (`dim_channels`, `dim_categories`, `dim_dates`). `dim_channels` is sourced from an SCD Type 2 snapshot — filter `is_current = true` when joining.

### Star Schema (Gold Layer)

**Fact Tables:**

| Model | Grain | Key Metrics |
|---|---|---|
| `fct_video_performance` | One row per video | `engagement_rate`, `like_to_view_ratio`, `comment_to_view_ratio`, `video_age_days` |
| `fct_comments` | One row per comment | `has_likes`, `has_replies`, `was_updated`, `comment_age_days` |
| `fct_searches` | One row per keyword + video + date | `search_rank`, `rank_change`, `keyword_daily_rank` |

**Dimension Tables:**

| Model | Description |
|---|---|
| `dim_channels` | Channel info with `channel_tier` (Nano/Micro/Macro/Mega) and `avg_views_per_video`. Sourced from SCD Type 2 snapshot |
| `dim_categories` | YouTube category lookup |
| `dim_dates` | Full date spine 2005–2030 with week, month, quarter, weekend flag |

### Silver Layer Rules

- Cast types, deduplicate, filter nulls, rename. No business logic.
- Simple extractions only: `EXTRACT(HOUR)`, `ARRAY_LENGTH`, boolean flags, ISO 8601 duration parsing
- All business metrics, ratios, and classifications belong in gold

### Snapshot — SCD Type 2

Tracks historical changes on channel metrics using dbt's `check` strategy:

```
check_cols: subscriber_count, video_count, total_view_count,
            channel_name, country, keywords
```

Current record identified by `dbt_valid_to IS NULL`. Always filter `is_current = true` when joining `dim_channels` to fact tables.

---

## Pipeline Automation (GitHub Actions)

The full pipeline runs automatically every week on GitHub's servers. No local machine required.

```
[Scheduled weekly — Wednesday 3am MYT]
            ↓
1.  Checkout repo
2.  Install Python dependencies
3.  Write GCP credentials from secret
4.  Run youtube_ingestion.py       →  GCS bronze
5.  Run load_gcs_to_bigquery.py    →  BigQuery bronze
6.  dbt deps
7.  dbt source freshness           ←  check data is fresh
8.  dbt run -s silver
9.  dbt test -s silver             ←  fail fast
10. dbt snapshot
11. dbt run -s gold
12. dbt test -s gold
13. Email alert on failure
```

**Fail fast principle:** source freshness and silver tests run before gold. A failure stops the pipeline early and triggers an email alert rather than propagating bad data downstream.

Pipeline can also be triggered manually at any time from the GitHub Actions tab.

---

## Data Quality

| Test Type | Applied To |
|---|---|
| `unique` + `not_null` | All primary keys across silver and gold |
| `not_null` | Critical foreign keys |
| `accepted_values` | `is_hd`, `assignable`, `channel_tier` |
| `relationships` | All FK to PK references across gold models |
| `source freshness` | All 5 bronze tables (warn: 25hr, error: 49hr) |

**Result: 56/56 dbt tests passing ✅ — 5/5 sources fresh ✅**

---

## Key Design Decisions

**ELT over ETL:** Raw data lands in GCS and BigQuery first. All transformation happens inside BigQuery via dbt. Raw data is always preserved and reprocessable.

**Bronze append only:** Bronze tables never modify or delete data. Each run appends a new day partition. A duplicate check prevents the same day being loaded twice.

**NDJSON format:** Files stored as newline-delimited JSON for native BigQuery load compatibility.

**Date partitioned GCS paths:** The `YYYY/MM/DD` folder structure mirrors BigQuery day partitioning and makes targeted reprocessing straightforward.

**Star schema in gold:** Fact and dimension tables follow Kimball's star schema pattern. Normalised structure keeps models clean, testable, and reusable across multiple BI tools. Chosen over a single wide OBT table in dbt — see tradeoff note below.

**OBT as a Looker Studio blend, not a dbt model:** A one-big-table joining all facts and dimensions could have been built in dbt, but was deliberately handled as a master blend in Looker Studio instead. This keeps the dbt gold layer clean, normalised, and reusable. The tradeoff is that the blend logic lives in the dashboard layer rather than being version-controlled in dbt, which is an acceptable tradeoff for this project scope.

**SCD Type 2 on channels:** Channel metrics like subscriber count change over time. dbt snapshots track historical changes so channel growth can be analysed over time. Current record identified by `is_current = true`.

**Fail fast pipeline:** Source freshness and silver tests run before gold models. A data quality failure stops the pipeline early rather than propagating bad data into the mart layer.

**`SAFE_DIVIDE` for all ratios:** Prevents division by zero on metrics like `engagement_rate` when `view_count = 0`, returning NULL instead of crashing.

**Exposures in dbt:** The Looker Studio dashboard is declared as a dbt exposure, connecting it to the lineage graph. This makes the full data journey visible end-to-end: API source to bronze to silver to gold to dashboard.

---

## Setup Instructions

### 1. Clone the repo

```bash
git clone https://github.com/mhdkerol/youtube-analytics-API.git
cd youtube-analytics-API
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

```bash
cp .env.example .env
```

Fill in your values:

```
YOUTUBE_API_KEY=your_youtube_api_key_here
GCS_BUCKET_NAME=your_bucket_name_here
GCP_PROJECT_ID=your_gcp_project_id_here
```

### 4. Add GCP credentials

Download your service account JSON key from GCP and save as `gcs_credentials.json` in the project root. It is listed in `.gitignore` and will never be committed.

### 5. Set up dbt virtual environment

```bash
python -m venv dbt-venv
dbt-venv\Scripts\activate        # Windows
pip install dbt-bigquery==1.11.1
```

### 6. Configure dbt profile

For local dbt runs, ensure you have a `profiles.yml` configured in `~/.dbt/` pointing to your BigQuery project. Example:

```yaml
youtube_analytics:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: your_gcp_project_id
      dataset: youtube_gold
      keyfile: /path/to/gcs_credentials.json
      location: US
      threads: 4
```

In GitHub Actions this is generated automatically from secrets. For local runs you need to set it up manually.

### 7. Run ingestion manually (optional)

```bash
python ingestion/youtube_ingestion.py
python ingestion/load_gcs_to_bigquery.py
```

### 8. Run dbt transformations manually (optional)

```bash
# From transformation/youtube_analytics/
dbt deps
dbt source freshness
dbt run -s silver
dbt test -s silver
dbt snapshot
dbt run -s gold
dbt test -s gold
dbt docs generate
dbt docs serve
```
