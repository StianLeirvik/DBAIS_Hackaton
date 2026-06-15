# Databricks notebook source
# MAGIC %md
# MAGIC # ▶️ Run All — CareMap pipeline orchestrator
# MAGIC
# MAGIC Runs the **entire** Bronze → Silver → Gold pipeline **in one shared session** using `%run`.
# MAGIC
# MAGIC `%run ./x` executes a notebook **inline in *this* notebook's context** — so all config,
# MAGIC helper functions, and variables stay in scope across steps (unlike `dbutils.notebook.run`,
# MAGIC which spawns an *isolated* job context with no shared state). The same-session payoff is the
# MAGIC verification summary at the bottom: it reads row counts across **every** layer in one place.
# MAGIC
# MAGIC **Run order** (sequential — each layer depends on the previous):
# MAGIC ```
# MAGIC 00_setup → 01_bronze_ingest → 02_silver_reference → 03_silver_facilities
# MAGIC          → 04_gold_dim_facility → 05_gold_evidence → 06_gold_reference
# MAGIC          → 07_gold_serving_views → 08_gold_user_persistence
# MAGIC ```
# MAGIC
# MAGIC > **Usage:** click **Run all** (or run top-to-bottom). Keep this notebook in the **same
# MAGIC > workspace folder** as `00–08` so the relative `%run` paths resolve. A failure stops the
# MAGIC > chain at the offending step, so the cell that errors tells you exactly where it broke.
# MAGIC >
# MAGIC > Each numbered notebook also `%run`s `00_setup` itself; re-running it is idempotent
# MAGIC > (`CREATE SCHEMA IF NOT EXISTS` + pure function/constant definitions), so the repeats are
# MAGIC > harmless.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 00 · Setup — config, schemas, helpers
# MAGIC Load config + helpers into *this* session too, so the summary cell can use `spark`,
# MAGIC the `*_SCHEMA_FQN` variables, and the shared helpers directly.

# COMMAND ----------

# MAGIC %run ./00_setup

# COMMAND ----------

from datetime import datetime

_t0 = datetime.now()
print('Pipeline started :', _t0.isoformat(timespec='seconds'))
print('Bronze schema    :', BRONZE_SCHEMA_FQN)
print('Silver schema    :', SILVER_SCHEMA_FQN)
print('Gold schema      :', GOLD_SCHEMA_FQN)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🥉 Bronze · 01 — raw ingest
# MAGIC Land the three provided Unity Catalog tables verbatim as Delta.

# COMMAND ----------

# MAGIC %run ./01_bronze_ingest

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🥈 Silver · 02 — reference dimensions
# MAGIC `dim_pincode` + `dim_district_health` (with validity-gate quarantine).

# COMMAND ----------

# MAGIC %run ./02_silver_reference

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🥈 Silver · 03 — facilities
# MAGIC Clean scalars/arrays, validate geography, and quarantine corrupted (non-UUID) rows.

# COMMAND ----------

# MAGIC %run ./03_silver_facilities

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🥇 Gold · 04 — dim_facility
# MAGIC Cluster dedup → one golden record per facility.

# COMMAND ----------

# MAGIC %run ./04_gold_dim_facility

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🥇 Gold · 05 — evidence
# MAGIC Explode claims with provenance, confidence, and reliability tagging; merge evidence band.

# COMMAND ----------

# MAGIC %run ./05_gold_evidence

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🥇 Gold · 06 — reference vocabularies
# MAGIC `dim_specialty` / `dim_care_need` / `bridge_care_need_specialty`.

# COMMAND ----------

# MAGIC %run ./06_gold_reference

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🥇 Gold · 07 — serving views + search
# MAGIC `vw_facility_enriched` + `search_referrals(location, care_need)`.

# COMMAND ----------

# MAGIC %run ./07_gold_serving_views

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🥇 Gold · 08 — user persistence
# MAGIC `user_*` tables + save/note/override/review helpers.

# COMMAND ----------

# MAGIC %run ./08_gold_user_persistence

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Pipeline summary
# MAGIC Same-session payoff: every layer's schema FQN is still in scope, so we verify row counts
# MAGIC across Bronze / Silver / Gold — including the quarantine split — in a single readout.

# COMMAND ----------

# Cross-layer row-count check. row_count is kept as a string so a missing table ('missing')
# doesn't break Spark's schema inference on a mixed int/str column.
_check = [
    ('Bronze', 'bronze_facilities',            f'{BRONZE_SCHEMA_FQN}.bronze_facilities'),
    ('Bronze', 'bronze_pincode',               f'{BRONZE_SCHEMA_FQN}.bronze_pincode'),
    ('Bronze', 'bronze_nfhs',                  f'{BRONZE_SCHEMA_FQN}.bronze_nfhs'),
    ('Silver', 'silver_facilities',            f'{SILVER_SCHEMA_FQN}.silver_facilities'),
    ('Silver', 'silver_facilities_quarantine', f'{SILVER_SCHEMA_FQN}.silver_facilities_quarantine'),
    ('Silver', 'dim_pincode',                  f'{SILVER_SCHEMA_FQN}.dim_pincode'),
    ('Silver', 'dim_district_health',          f'{SILVER_SCHEMA_FQN}.dim_district_health'),
    ('Gold',   'dim_facility',                 f'{GOLD_SCHEMA_FQN}.dim_facility'),
    ('Gold',   'facility_procedure',           f'{GOLD_SCHEMA_FQN}.facility_procedure'),
    ('Gold',   'facility_specialty',           f'{GOLD_SCHEMA_FQN}.facility_specialty'),
    ('Gold',   'facility_source',              f'{GOLD_SCHEMA_FQN}.facility_source'),
    ('Gold',   'facility_contact',             f'{GOLD_SCHEMA_FQN}.facility_contact'),
    ('Gold',   'facility_evidence_summary',    f'{GOLD_SCHEMA_FQN}.facility_evidence_summary'),
    ('Gold',   'dim_specialty',                f'{GOLD_SCHEMA_FQN}.dim_specialty'),
    ('Gold',   'dim_care_need',                f'{GOLD_SCHEMA_FQN}.dim_care_need'),
    ('Gold',   'bridge_care_need_specialty',   f'{GOLD_SCHEMA_FQN}.bridge_care_need_specialty'),
]

def _count(fqn):
    try:
        return str(spark.table(fqn).count())
    except Exception:
        return 'missing'

summary = spark.createDataFrame(
    [(layer, name, _count(fqn)) for layer, name, fqn in _check],
    ['layer', 'table', 'row_count'])
summary.show(len(_check), truncate=False)

# COMMAND ----------

try:
    _elapsed = (datetime.now() - _t0).total_seconds()
    print(f'✅ Pipeline finished in {_elapsed:.0f}s — all layers rebuilt in one session.')
except NameError:
    print('✅ Pipeline finished (run from the top to see total duration).')
