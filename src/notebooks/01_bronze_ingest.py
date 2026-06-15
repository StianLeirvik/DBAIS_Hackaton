# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Bronze — raw ingest
# MAGIC
# MAGIC Land all three **provided Unity Catalog tables** verbatim as Delta (no transforms — auditability).
# MAGIC Adds lineage columns `_source_table` and `_ingest_ts`.
# MAGIC
# MAGIC | Bronze table | Source UC table |
# MAGIC |---|---|
# MAGIC | `bronze_facilities` | `SOURCE_FACILITIES_TABLE` |
# MAGIC | `bronze_pincode` | `SOURCE_PINCODE_TABLE` |
# MAGIC | `bronze_nfhs` | `SOURCE_NFHS_TABLE` |

# COMMAND ----------

# MAGIC %run ./00_setup

# COMMAND ----------

# Facilities — provided Unity Catalog table, landed verbatim.
fac = (spark.table(SOURCE_FACILITIES_TABLE)
       .withColumn('_source_table', F.lit(SOURCE_FACILITIES_TABLE))
       .withColumn('_ingest_ts', F.current_timestamp()))
write_table(fac, 'bronze_facilities')

# COMMAND ----------

# Pincode directory — provided Unity Catalog table.
pincode = (spark.table(SOURCE_PINCODE_TABLE)
           .withColumn('_source_table', F.lit(SOURCE_PINCODE_TABLE))
           .withColumn('_ingest_ts', F.current_timestamp()))
write_table(pincode, 'bronze_pincode')

# COMMAND ----------

# NFHS-5 district indicators — provided Unity Catalog table.
nfhs = (spark.table(SOURCE_NFHS_TABLE)
        .withColumn('_source_table', F.lit(SOURCE_NFHS_TABLE))
        .withColumn('_ingest_ts', F.current_timestamp()))
write_table(nfhs, 'bronze_nfhs')

# COMMAND ----------

for t in ['bronze_facilities', 'bronze_pincode', 'bronze_nfhs']:
    print(f'{t:20s}', spark.table(f'{SCHEMA_FQN}.{t}').count(), 'rows')
