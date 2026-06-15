# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Setup — Referral Copilot
# MAGIC
# MAGIC Shared **config**, **schema/volume** creation, and reusable **helper functions**.
# MAGIC
# MAGIC Run this first. Every other notebook starts with `%run ./00_setup` so they share these values and helpers.

# COMMAND ----------

# ===== Catalog / schema =====
CATALOG = 'workspace'                 # Free Edition default catalog
SCHEMA  = 'referral_copilot'          # all bronze/silver/gold tables live here
SCHEMA_FQN = f'{CATALOG}.{SCHEMA}'

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

def write_table(df, name, mode='overwrite'):
    '''Write a managed Delta table into the project schema.'''
    (df.write.mode(mode)
        .option('overwriteSchema', 'true')
        .saveAsTable(f'{SCHEMA_FQN}.{name}'))

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
