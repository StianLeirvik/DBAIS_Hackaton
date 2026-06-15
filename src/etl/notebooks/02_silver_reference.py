# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Silver — reference dimensions
# MAGIC
# MAGIC Builds the two reference tables the facility cleaning depends on:
# MAGIC
# MAGIC - **`dim_pincode`** — one row per 6-digit pincode with a validated centroid (avg of in-India office coords).
# MAGIC - **`dim_district_health`** — NFHS-5 district indicators cleaned (`*` → NULL + `has_suppressed_values`, `(x)` small-sample markers stripped).

# COMMAND ----------

# MAGIC %run ./00_setup

# COMMAND ----------

# MAGIC %md
# MAGIC ## dim_pincode
# MAGIC Drop `NA` coords, keep only in-India points, aggregate to one centroid per pincode.

# COMMAND ----------

bp = spark.table(f'{BRONZE_SCHEMA_FQN}.bronze_pincode')

# dim_facility (Gold) carries an FK to dim_pincode; drop it first so this overwrite is allowed.
drop_all_fks()

pin = (bp
       .withColumn('pincode', F.regexp_extract(F.col('pincode'), r'(\d{6})', 1))
       .withColumn('lat', to_double(F.col('latitude')))
       .withColumn('lon', to_double(F.col('longitude')))
       .withColumn('district', norm_text(F.col('district')))
       .withColumn('state', norm_text(F.col('statename')))
       .filter((F.col('pincode') != '') & F.col('lat').isNotNull() & F.col('lon').isNotNull())
       .filter(is_valid_india_coord(F.col('lat'), F.col('lon'))))

dim_pincode = (pin.groupBy('pincode')
               .agg(F.round(F.avg('lat'), 6).alias('centroid_lat'),
                    F.round(F.avg('lon'), 6).alias('centroid_long'),
                    F.first('district', ignorenulls=True).alias('district'),
                    F.first('state', ignorenulls=True).alias('state'),
                    F.count('*').alias('office_count')))
write_table(dim_pincode, 'dim_pincode', SILVER_SCHEMA_FQN)
add_pk('dim_pincode', 'pincode', SILVER_SCHEMA_FQN, rely=True)

# COMMAND ----------

# MAGIC %md
# MAGIC ## dim_district_health
# MAGIC Curated referral-relevant indicators. `*` = suppressed → NULL; `(value)` small-sample markers stripped; numbers cast to double.

# COMMAND ----------

bn = spark.table(f'{BRONZE_SCHEMA_FQN}.bronze_nfhs')

def clean_nfhs(colname):
    cc = F.trim(F.col(colname))
    cc = F.regexp_replace(cc, r'[()]', '')          # strip small-sample markers
    return to_double(cc)                              # '*', 'NA', blanks -> NULL safely

# raw column name -> friendly name
indicators = {
    'institutional_birth_5y_pct': 'institutional_birth_5y_pct',
    'institutional_birth_in_public_facility_5y_pct': 'institutional_birth_public_5y_pct',
    'hh_member_covered_health_insurance_pct': 'hh_health_insurance_pct',
    'mothers_who_had_at_least_4_anc_visits_lb5y_pct': 'anc_4plus_visits_pct',
    'births_delivered_by_csection_5y_pct': 'csection_5y_pct',
    'child_12_23m_fully_vaccinated_based_on_information_from_vax_pct': 'child_fully_vaccinated_pct',
    'all_w15_49_who_are_anaemic_pct': 'women_anaemic_pct',
}

sel = [norm_text(F.col('district_name')).alias('district_name'),
       norm_text(F.col('state_ut')).alias('state_ut')]
sel += [clean_nfhs(raw).alias(new) for raw, new in indicators.items()]

dim_health = (bn.select(*sel)
              .withColumn('district_state_key', F.concat_ws('|', 'district_name', 'state_ut')))

# flag rows where any selected indicator was suppressed
suppressed = None
for c in indicators.values():
    cond = F.col(c).isNull()
    suppressed = cond if suppressed is None else (suppressed | cond)
dim_health = dim_health.withColumn('has_suppressed_values', suppressed)
write_table(dim_health, 'dim_district_health', SILVER_SCHEMA_FQN)
add_pk('dim_district_health', 'district_state_key', SILVER_SCHEMA_FQN, rely=True)
