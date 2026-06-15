# src · Referral Copilot data pipeline

Databricks (Free Edition) Medallion pipeline that turns the 10,000 messy Indian
healthcare facility records into an **evidence-attached, uncertainty-aware** referral
dataset for the Referral Copilot app.

Design rationale lives in [../EDA](../EDA): data overview, quality issues, cleaning
route, and the target schema / ERD. This folder is the runnable implementation of it.

## Layout

```
src/
  README.md
  config.py                  # table names + constants (importable by the app layer)
  seeds/                     # version-controlled reference vocabularies
    dim_specialty.csv
    dim_care_need.csv
    bridge_care_need_specialty.csv
  notebooks/                 # Databricks source-format notebooks (.py)
    00_setup.py              # config, schema/volume, shared helper functions
    01_bronze_ingest.py      # read provided UC tables -> bronze_* Delta (verbatim)
    02_silver_reference.py   # dim_pincode + dim_district_health
    03_silver_facilities.py  # clean facilities (nulls, JSON arrays, casts, geo validation)
    04_gold_dim_facility.py  # cluster dedup -> golden facility record
    05_gold_evidence.py      # explode claims + provenance + confidence + evidence_band
    06_gold_reference.py     # dim_specialty / dim_care_need / bridge (from seeds)
    07_gold_serving_views.py # vw_facility_enriched + search_referrals()
    08_gold_user_persistence.py # user_* tables + save/note/override/review helpers
```

> The notebooks are **Databricks source-format `.py` files** (`# Databricks notebook source`,
> cells split by `# COMMAND ----------`). They import as real notebooks in the Databricks
> workspace (Repos sync or **Workspace → Import**) and stay clean in git. Open them in the
> Databricks notebook editor to run.

## Run order

Run the notebooks in numeric order in the Databricks workspace. Each one starts with
`%run ./00_setup`, so they share the same config and helper functions (keep them in the
same workspace folder so the relative `%run` resolves).

```
00_setup → 01_bronze_ingest → 02_silver_reference → 03_silver_facilities
        → 04_gold_dim_facility → 05_gold_evidence → 06_gold_reference
        → 07_gold_serving_views → 08_gold_user_persistence
```

## Sources

All three raw sources are **read-only Unity Catalog tables** provided by the hackathon.
The Bronze layer reads them directly with `spark.table(...)` — there is no CSV upload step.

| Source | Unity Catalog table | Bronze output |
|---|---|---|
| Facilities (10k × 51 cols) | `databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities` | `bronze_facilities` |
| Pincode directory | `…virtue_foundation_dataset.india_post_pincode_directory` | `bronze_pincode` |
| NFHS-5 indicators | `…virtue_foundation_dataset.nfhs_5_district_health_indicators` | `bronze_nfhs` |

> The fully-qualified source names live in [config.py](config.py) (`SOURCE_*_TABLE`) and are
> mirrored in `00_setup`. On Free Edition the project's own output tables are created in the
> `workspace.referral_copilot` schema.

## What the app consumes (Gold)

- `dim_facility` — one golden record per facility (deduped by `cluster_id`) with
  `geo_is_valid`, `geo_source`, `state_mismatch`, `data_quality_score`, `evidence_band`.
- `facility_specialty` / `facility_procedure` / `facility_equipment` / `facility_capability`
  — exploded **claims to verify**, each with a `confidence` and a citation URL.
- `facility_source` / `facility_contact` — citations + contact channels.
- `vw_facility_enriched` + `search_referrals(location, care_need)` — location + need in,
  ranked candidates out (distance, matching evidence, missing/suspicious evidence, citations).
- `user_*` — persisted scenarios, shortlists, notes, overrides, and review decisions.

## Honesty / uncertainty signals (never hide weak evidence)

`geo_is_valid`, `geo_source` (raw vs pincode fallback), `state_mismatch`, per-claim
`confidence`, facility `evidence_band` (High/Medium/Low), and NFHS `has_suppressed_values`.
