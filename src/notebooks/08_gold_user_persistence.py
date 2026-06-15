# Databricks notebook source
# MAGIC %md
# MAGIC # 08 · Gold — user persistence
# MAGIC
# MAGIC Delta tables + helper functions that let the app **save and revise** user work, satisfying
# MAGIC the requirement to persist notes, overrides, shortlists, scenarios, and review decisions.
# MAGIC
# MAGIC | Table | Purpose |
# MAGIC |---|---|
# MAGIC | `user_scenario` | a saved search (location + need + params) |
# MAGIC | `user_shortlist` / `user_shortlist_item` | named shortlists of candidates |
# MAGIC | `user_note` | free-text notes on a facility |
# MAGIC | `user_override` | user corrections to a field (keeps original + reason) |
# MAGIC | `user_review_decision` | verify / reject / needs-info on a specific claim |

# COMMAND ----------

# MAGIC %run ./00_setup

# COMMAND ----------

ddls = [
    '''CREATE TABLE IF NOT EXISTS {s}.user_scenario (
        scenario_id STRING, user_id STRING, location_query STRING, care_need STRING,
        params_json STRING, created_at TIMESTAMP) USING DELTA''',
    '''CREATE TABLE IF NOT EXISTS {s}.user_shortlist (
        shortlist_id STRING, user_id STRING, scenario_id STRING, name STRING,
        created_at TIMESTAMP) USING DELTA''',
    '''CREATE TABLE IF NOT EXISTS {s}.user_shortlist_item (
        shortlist_id STRING, facility_id STRING, rank INT, distance_km DOUBLE,
        added_at TIMESTAMP) USING DELTA''',
    '''CREATE TABLE IF NOT EXISTS {s}.user_note (
        note_id STRING, user_id STRING, facility_id STRING, note_text STRING,
        created_at TIMESTAMP) USING DELTA''',
    '''CREATE TABLE IF NOT EXISTS {s}.user_override (
        override_id STRING, user_id STRING, facility_id STRING, field_name STRING,
        original_value STRING, override_value STRING, reason STRING, created_at TIMESTAMP) USING DELTA''',
    '''CREATE TABLE IF NOT EXISTS {s}.user_review_decision (
        review_id STRING, user_id STRING, facility_id STRING, claim_ref STRING,
        decision STRING, created_at TIMESTAMP) USING DELTA''',
]
for ddl in ddls:
    spark.sql(ddl.format(s=SCHEMA_FQN))
print('user_* tables ready')

# COMMAND ----------

import uuid, json, datetime
from pyspark.sql.types import (StructType, StructField, StringType, IntegerType,
                               DoubleType, TimestampType)

def _now():
    return datetime.datetime.utcnow()

def _append(rows, schema, table):
    spark.createDataFrame(rows, schema).write.mode('append').saveAsTable(f'{SCHEMA_FQN}.{table}')

_SCEN = StructType([StructField('scenario_id', StringType()), StructField('user_id', StringType()),
                    StructField('location_query', StringType()), StructField('care_need', StringType()),
                    StructField('params_json', StringType()), StructField('created_at', TimestampType())])
_SL = StructType([StructField('shortlist_id', StringType()), StructField('user_id', StringType()),
                  StructField('scenario_id', StringType()), StructField('name', StringType()),
                  StructField('created_at', TimestampType())])
_SLI = StructType([StructField('shortlist_id', StringType()), StructField('facility_id', StringType()),
                   StructField('rank', IntegerType()), StructField('distance_km', DoubleType()),
                   StructField('added_at', TimestampType())])
_NOTE = StructType([StructField('note_id', StringType()), StructField('user_id', StringType()),
                    StructField('facility_id', StringType()), StructField('note_text', StringType()),
                    StructField('created_at', TimestampType())])
_OVR = StructType([StructField('override_id', StringType()), StructField('user_id', StringType()),
                   StructField('facility_id', StringType()), StructField('field_name', StringType()),
                   StructField('original_value', StringType()), StructField('override_value', StringType()),
                   StructField('reason', StringType()), StructField('created_at', TimestampType())])
_REV = StructType([StructField('review_id', StringType()), StructField('user_id', StringType()),
                   StructField('facility_id', StringType()), StructField('claim_ref', StringType()),
                   StructField('decision', StringType()), StructField('created_at', TimestampType())])

def save_scenario(user_id, location_query, care_need, params=None):
    sid = str(uuid.uuid4())
    _append([(sid, user_id, location_query, care_need, json.dumps(params or {}), _now())], _SCEN, 'user_scenario')
    return sid

def create_shortlist(user_id, name, scenario_id=None):
    slid = str(uuid.uuid4())
    _append([(slid, user_id, scenario_id, name, _now())], _SL, 'user_shortlist')
    return slid

def add_to_shortlist(shortlist_id, facility_id, rank=None, distance_km=None):
    _append([(shortlist_id, facility_id, rank, distance_km, _now())], _SLI, 'user_shortlist_item')

def add_note(user_id, facility_id, text):
    _append([(str(uuid.uuid4()), user_id, facility_id, text, _now())], _NOTE, 'user_note')

def add_override(user_id, facility_id, field_name, original_value, override_value, reason=''):
    _append([(str(uuid.uuid4()), user_id, facility_id, field_name, original_value, override_value, reason, _now())], _OVR, 'user_override')

def add_review_decision(user_id, facility_id, claim_ref, decision):
    _append([(str(uuid.uuid4()), user_id, facility_id, claim_ref, decision, _now())], _REV, 'user_review_decision')

print('persistence helpers ready: save_scenario, create_shortlist, add_to_shortlist, add_note, add_override, add_review_decision')

# COMMAND ----------

# Demo: persist a full user workflow
uid = 'demo_user'
sid = save_scenario(uid, 'Ahmedabad', 'orthopedics', {'max_km': 50})
slid = create_shortlist(uid, 'Ortho near Ahmedabad', sid)
fid = spark.table(f'{SCHEMA_FQN}.dim_facility').select('facility_id').first()['facility_id']
add_to_shortlist(slid, fid, rank=1, distance_km=4.2)
add_note(uid, fid, 'Confirmed 24/7 emergency by phone.')
add_override(uid, fid, 'capacity_beds', None, '120', 'Verified from hospital brochure')
add_review_decision(uid, fid, 'capability:24/7 emergency', 'verified')

print('shortlist items:')
spark.table(f'{SCHEMA_FQN}.user_shortlist_item').show(truncate=False)
