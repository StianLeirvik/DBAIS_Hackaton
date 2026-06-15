# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Gold — dim_facility (golden record)
# MAGIC
# MAGIC Resolve duplicate records that refer to the same facility (grouped by `cluster_id`)
# MAGIC into **one golden record**, keeping the cluster member ids for evidence/citation.
# MAGIC
# MAGIC The winning record per cluster is the most complete one (`completeness_score`).
# MAGIC `evidence_band` / `evidence_strength` are populated later in `05_gold_evidence`.

# COMMAND ----------

# MAGIC %run ./00_setup

# COMMAND ----------

from pyspark.sql.window import Window

s = spark.table(f'{SILVER_SCHEMA_FQN}.silver_facilities')

s = (s
     .withColumn('cluster_key', F.coalesce(F.col('cluster_id'), F.col('facility_id')))
     .withColumn('n_specialties', F.size(F.coalesce(F.col('specialties_arr'), F.array())))
     .withColumn('n_procedures', F.size(F.coalesce(F.col('procedure_arr'), F.array())))
     .withColumn('n_equipment', F.size(F.coalesce(F.col('equipment_arr'), F.array())))
     .withColumn('n_capability', F.size(F.coalesce(F.col('capability_arr'), F.array())))
     .withColumn('n_sources', F.size(F.coalesce(F.col('source_urls_arr'), F.array()))))

# completeness 0..1 across structured fields + evidence coverage
s = s.withColumn('completeness_score', (
        F.col('year_established').isNotNull().cast('double') +
        F.col('capacity_beds').isNotNull().cast('double') +
        F.col('number_doctors').isNotNull().cast('double') +
        F.col('email').isNotNull().cast('double') +
        F.col('official_website').isNotNull().cast('double') +
        F.least(F.col('n_specialties') / F.lit(5.0), F.lit(1.0)) +
        F.least(F.col('n_capability') / F.lit(5.0), F.lit(1.0)) +
        F.least(F.col('n_sources') / F.lit(3.0), F.lit(1.0))
     ) / F.lit(8.0))

w = Window.partitionBy('cluster_key').orderBy(
        F.desc('completeness_score'), F.desc('n_capability'), F.desc('n_sources'))
golden = (s.withColumn('rn', F.row_number().over(w))
            .filter(F.col('rn') == 1)
            .drop('rn'))

members = (s.groupBy('cluster_key')
             .agg(F.collect_set('facility_id').alias('member_ids'),
                  F.count('*').alias('cluster_size')))

# COMMAND ----------

dim = (golden.join(members, on='cluster_key', how='left')
       .withColumn('data_quality_score', F.round(
            0.6 * F.col('completeness_score') +
            0.2 * F.col('geo_is_valid').cast('double') +
            0.2 * (F.lit(1.0) - F.coalesce(F.col('state_mismatch').cast('double'), F.lit(0.0))), 3))
       .withColumn('evidence_band', F.lit(None).cast('string'))      # set in 05_gold_evidence
       .withColumn('evidence_strength', F.lit(None).cast('double')))

dim_out = dim.select(
    'facility_id', 'cluster_key', 'cluster_size', 'member_ids',
    'name_clean', 'facility_type', 'operator_type', 'description',
    'year_established', 'capacity_beds', 'number_doctors',
    'city', 'state', 'pincode', 'pin_district',
    'latitude_clean', 'longitude_clean', 'geo_is_valid', 'geo_source', 'state_mismatch',
    'official_website', 'official_phone', 'email', 'facebook_link', 'recency',
    'specialties_arr', 'procedure_arr', 'equipment_arr', 'capability_arr',
    'source_urls_arr', 'source_types_arr', 'phones_arr', 'websites_arr',
    'n_specialties', 'n_procedures', 'n_equipment', 'n_capability', 'n_sources',
    'data_quality_score', 'evidence_band', 'evidence_strength')
write_table(dim_out, 'dim_facility')

# COMMAND ----------

d = spark.table(f'{SCHEMA_FQN}.dim_facility')
print('golden facilities:', d.count())
(d.select('name_clean', 'city', 'state', 'cluster_size', 'data_quality_score')
   .orderBy(F.desc('cluster_size')).show(10, truncate=False))
