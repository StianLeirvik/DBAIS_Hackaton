# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Setup — Referral Copilot
# MAGIC
# MAGIC Shared **config**, **schema/volume** creation, and reusable **helper functions**.
# MAGIC
# MAGIC Run this first. Every other notebook starts with `%run ./00_setup` so they share these values and helpers.

# COMMAND ----------

# ===== Catalog / per-layer schemas (databases) =====
# Each medallion layer gets its OWN database (schema); Gold (serving) stays in the
# current/project database. Cross-layer reads use the explicit *_SCHEMA_FQN below.
CATALOG = 'workspace'                       # Free Edition default catalog
GOLD_SCHEMA   = 'referral_copilot'          # Gold (serving) — the current project database
BRONZE_SCHEMA = 'referral_copilot_bronze'   # Bronze (raw landing)
SILVER_SCHEMA = 'referral_copilot_silver'   # Silver (cleaned / conformed)

GOLD_SCHEMA_FQN   = f'{CATALOG}.{GOLD_SCHEMA}'
BRONZE_SCHEMA_FQN = f'{CATALOG}.{BRONZE_SCHEMA}'
SILVER_SCHEMA_FQN = f'{CATALOG}.{SILVER_SCHEMA}'

# Default schema for write_table() and gold-to-gold reads.
SCHEMA = GOLD_SCHEMA
SCHEMA_FQN = GOLD_SCHEMA_FQN

# ===== Source data (read-only Unity Catalog tables, provided by the hackathon) =====
# All three raw sources already exist as UC tables; Bronze reads them directly.
SOURCE_CATALOG    = 'databricks_virtue_foundation_dataset_dais_2026'
SOURCE_SCHEMA     = 'virtue_foundation_dataset'
SOURCE_SCHEMA_FQN = f'{SOURCE_CATALOG}.{SOURCE_SCHEMA}'
SOURCE_FACILITIES_TABLE = f'{SOURCE_SCHEMA_FQN}.facilities'
SOURCE_PINCODE_TABLE    = f'{SOURCE_SCHEMA_FQN}.india_post_pincode_directory'
SOURCE_NFHS_TABLE       = f'{SOURCE_SCHEMA_FQN}.nfhs_5_district_health_indicators'

# ===== Validation constants =====
INDIA_LAT_MIN, INDIA_LAT_MAX = 6.0, 38.0
INDIA_LON_MIN, INDIA_LON_MAX = 68.0, 98.0
YEAR_MIN, YEAR_MAX = 1850, 2026

# ===== Confidence weights (transparent + tunable) =====
W_AUTHORITY, W_CORROBORATION, W_RECENCY = 0.5, 0.3, 0.2
CORROBORATION_CAP = 3                  # diminishing returns past 3 corroborating sources

# ===== Reliability tagging (per claim: can the facility actually do this?) =====
# We KEEP every record and never silently drop quality errors — instead each claim is
# tagged Reliable / Uncertain / Unreliable with a human-readable reason. A claim is
# 'corroborated' when its keywords also appear in the facility's OTHER evidence fields
# (equipment / specialty / capability) — true cross-field support. Both knobs are tunable.
RELIABLE_MIN_SOURCES = 2               # >= this many distinct sources counts as corroborated
KEYWORD_MIN_LEN = 5                    # min token length when extracting claim keywords

print('Config loaded for', SCHEMA_FQN)

# COMMAND ----------

# Create the project schema. Raw data is read directly from the provided UC tables,
# so no volume or CSV-upload step is required.
spark.sql(f'CREATE SCHEMA IF NOT EXISTS {SCHEMA_FQN}') # pylint: disable=E0602 # defined in dbruntime
print('Schema ready:', SCHEMA_FQN)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper functions
# MAGIC
# MAGIC Small, reusable column expressions used across Silver/Gold: null normalization, JSON-array
# MAGIC parsing, India geo validation, haversine distance, and a table writer.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, StringType

_NULL_TOKENS = ['null', 'NULL', 'Null', 'na', 'NA', 'N/A', 'none', 'None', 'NONE', '', '[]', '{}']

def clean_null(c):
    '''Turn literal null-ish strings into real NULLs.'''
    cc = F.trim(c)
    return F.when(cc.isin(*_NULL_TOKENS), None).otherwise(cc)

_NUM_RE = r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$'

def to_double(c):
    '''ANSI-safe string->double: non-numeric values ('NA', '*', '', text) become NULL
    instead of raising CAST_INVALID_INPUT. Invalid entries are NULLed BEFORE the cast,
    so it is safe regardless of CASE-WHEN short-circuit behaviour.'''
    s = F.trim(c.cast('string'))
    s = F.when(s.rlike(_NUM_RE), s).otherwise(None)
    return s.cast('double')

def to_int(c):
    '''ANSI-safe string->int via double (handles '100', '100.0'; malformed -> NULL).'''
    return to_double(c).cast('int')

def parse_json_array(c):
    '''Parse a JSON-encoded string array into a deduped array<string> (nulls/blanks dropped).'''
    arr = F.from_json(c, ArrayType(StringType()))
    arr = F.filter(arr, lambda x: x.isNotNull() & (F.trim(x) != ''))
    return F.array_distinct(arr)

def is_valid_india_coord(lat, lon):
    '''True when a lat/lon falls inside the India bounding box.'''
    return lat.between(INDIA_LAT_MIN, INDIA_LAT_MAX) & lon.between(INDIA_LON_MIN, INDIA_LON_MAX)

def haversine_km(lat1, lon1, lat2, lon2):
    '''Great-circle distance in km between two points, as a Spark Column.'''
    dlat = F.radians(lat2 - lat1)
    dlon = F.radians(lon2 - lon1)
    a = (F.pow(F.sin(dlat / 2), 2) +
         F.cos(F.radians(lat1)) * F.cos(F.radians(lat2)) * F.pow(F.sin(dlon / 2), 2))
    return F.lit(6371.0) * 2 * F.asin(F.sqrt(a))

def norm_text(c):
    '''Trim + upper-case for join keys.'''
    return F.upper(F.trim(c))

def write_table(df, name, schema_fqn=None, mode='overwrite'):
    '''Write a managed Delta table into `schema_fqn` (defaults to the Gold database).
    Pass BRONZE_SCHEMA_FQN / SILVER_SCHEMA_FQN to land a table in another layer.'''
    target = schema_fqn or GOLD_SCHEMA_FQN
    (df.write.mode(mode)
        .option('overwriteSchema', 'true')
        .saveAsTable(f'{target}.{name}'))

# ----- Reliability tagging helpers -----
_STOPWORDS = ['provides', 'provide', 'provided', 'offers', 'offer', 'offered', 'available',
              'services', 'service', 'patient', 'patients', 'treatment', 'treatments',
              'performs', 'perform', 'performed', 'using', 'during', 'routine', 'general',
              'department', 'departments', 'facility', 'facilities', 'hospital', 'clinic',
              'center', 'centre', 'medical', 'care', 'based', 'listed', 'include', 'includes',
              'including', 'located', 'onsite', 'within', 'available']

def keywords(c):
    '''Free text -> distinct lowercase keyword tokens (letters only, len >= KEYWORD_MIN_LEN, stopwords dropped).'''
    toks = F.split(F.lower(c), r'[^a-z]+')
    toks = F.filter(toks, lambda x: (F.length(x) >= F.lit(KEYWORD_MIN_LEN)) & ~x.isin(*_STOPWORDS))
    return F.array_distinct(toks)

def reliability_expr(has_official, n_sources, matched_terms, geo_valid):
    '''Return (is_reliable, reliability, reliability_reason) Column expressions for one claim.

    Signals (all Columns):
      has_official  : the facility has an official-website source (authority)
      n_sources     : count of distinct corroborating sources
      matched_terms : claim keywords also found in the facility's OTHER evidence (cross-field support)
      geo_valid     : the facility location passed India bbox validation
    '''
    strong_source = has_official | (n_sources >= F.lit(RELIABLE_MIN_SOURCES))
    has_support = F.size(F.coalesce(matched_terms, F.array())) > 0

    reasons = F.filter(F.array(
        F.when(has_official, F.lit('backed by official website')),
        F.when(~has_official & (n_sources >= F.lit(RELIABLE_MIN_SOURCES)),
               F.concat(F.lit('corroborated by '), n_sources.cast('string'), F.lit(' independent sources'))),
        F.when(has_support, F.concat(F.lit('supported by equipment/specialty evidence ('),
               F.array_join(F.slice(matched_terms, 1, 3), ', '), F.lit(')'))),
        F.when(~strong_source, F.lit('only a single low-authority source')),
        F.when(~has_support, F.lit('no corroborating equipment/specialty evidence')),
        F.when(~geo_valid, F.lit('facility location could not be verified')),
    ), lambda x: x.isNotNull())
    reason = F.concat_ws('; ', reasons)

    reliability = (F.when(strong_source & has_support, F.lit('Reliable'))
                    .when(~strong_source & ~has_support, F.lit('Unreliable'))
                    .otherwise(F.lit('Uncertain')))
    is_reliable = reliability == F.lit('Reliable')
    return is_reliable, reliability, reason

# ----- Primary / foreign key helpers (Unity Catalog: informational, NOT enforced) -----
# Databricks does NOT enforce PK/FK — they are metadata that powers Catalog Explorer's ERD,
# BI-tool joins, and (with RELY) optimizer rewrites. We DO enforce NOT NULL on PK columns
# (a PK requirement) but keep every other column nullable, so messy records are kept and
# tagged, never rejected. RELY is opt-in — only set it where uniqueness genuinely holds.
#
# Registry of every pipeline FK so a parent can drop the child FKs before it is overwritten
# (UC blocks overwriting a table that an FK references). FKs are re-added by the child
# notebooks later in a normal top-to-bottom run, so this keeps full re-runs safe.
PIPELINE_FKS = [
    # (schema_fqn, child_table, fk_name)
    (GOLD_SCHEMA_FQN, 'dim_facility',               'fk_dim_facility_pincode'),
    (GOLD_SCHEMA_FQN, 'facility_procedure',         'fk_facility_procedure_facility'),
    (GOLD_SCHEMA_FQN, 'facility_equipment',         'fk_facility_equipment_facility'),
    (GOLD_SCHEMA_FQN, 'facility_capability',        'fk_facility_capability_facility'),
    (GOLD_SCHEMA_FQN, 'facility_specialty',         'fk_facility_specialty_facility'),
    (GOLD_SCHEMA_FQN, 'facility_source',            'fk_facility_source_facility'),
    (GOLD_SCHEMA_FQN, 'facility_contact',           'fk_facility_contact_facility'),
    (GOLD_SCHEMA_FQN, 'facility_evidence_summary',  'fk_facility_evidence_summary_facility'),
    (GOLD_SCHEMA_FQN, 'bridge_care_need_specialty', 'fk_bridge_care_need'),
    (GOLD_SCHEMA_FQN, 'bridge_care_need_specialty', 'fk_bridge_specialty'),
    (GOLD_SCHEMA_FQN, 'user_shortlist',             'fk_user_shortlist_scenario'),
    (GOLD_SCHEMA_FQN, 'user_shortlist_item',        'fk_user_shortlist_item_shortlist'),
]

def _safe_sql(q):
    '''Run SQL, swallowing errors (used for best-effort DROP CONSTRAINT on maybe-missing tables).'''
    try:
        spark.sql(q)
    except Exception:
        pass

def drop_all_fks():
    '''Drop every pipeline FK (if present) so referenced parent tables can be overwritten.
    Call at the top of any notebook that overwrites a parent table.'''
    for sfqn, tbl, fk in PIPELINE_FKS:
        _safe_sql(f'ALTER TABLE {sfqn}.{tbl} DROP CONSTRAINT IF EXISTS {fk}')

def add_pk(name, cols, schema_fqn=None, rely=False):
    '''Set NOT NULL on the PK column(s) + (re)create an informational PRIMARY KEY (idempotent).
    rely=True lets the optimizer trust it — only where the key is genuinely unique.'''
    target = schema_fqn or GOLD_SCHEMA_FQN
    fqn = f'{target}.{name}'
    cols = [cols] if isinstance(cols, str) else list(cols)
    for c in cols:
        spark.sql(f'ALTER TABLE {fqn} ALTER COLUMN {c} SET NOT NULL')
    spark.sql(f'ALTER TABLE {fqn} DROP CONSTRAINT IF EXISTS pk_{name}')
    spark.sql(f'ALTER TABLE {fqn} ADD CONSTRAINT pk_{name} PRIMARY KEY ({", ".join(cols)})'
              + (' RELY' if rely else ''))
    print(f'  PK pk_{name} ({", ".join(cols)}) on {fqn}')

def add_fk(name, fk_name, cols, ref_fqn, ref_cols, schema_fqn=None):
    '''(Re)create an informational FOREIGN KEY (idempotent). The parent must already have a
    PRIMARY KEY/UNIQUE on ref_cols. Not enforced — surfaces the relationship in the ERD.'''
    target = schema_fqn or GOLD_SCHEMA_FQN
    fqn = f'{target}.{name}'
    cols = [cols] if isinstance(cols, str) else list(cols)
    ref_cols = [ref_cols] if isinstance(ref_cols, str) else list(ref_cols)
    spark.sql(f'ALTER TABLE {fqn} DROP CONSTRAINT IF EXISTS {fk_name}')
    spark.sql(f'ALTER TABLE {fqn} ADD CONSTRAINT {fk_name} '
              f'FOREIGN KEY ({", ".join(cols)}) REFERENCES {ref_fqn} ({", ".join(ref_cols)})')
    print(f'  FK {fk_name}: {name}({", ".join(cols)}) -> {ref_fqn}({", ".join(ref_cols)})')
