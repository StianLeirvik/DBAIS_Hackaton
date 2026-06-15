# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Silver — facilities
# MAGIC
# MAGIC Clean the facility records: normalize null-ish strings, parse JSON-encoded arrays,
# MAGIC cast numerics, and **validate geography** (India bounding box, with a `dim_pincode`
# MAGIC centroid fallback when raw coordinates are out of range).
# MAGIC
# MAGIC Honesty columns produced: `geo_is_valid`, `geo_source`, `state_mismatch`.

# COMMAND ----------

# MAGIC %run ./00_setup

# COMMAND ----------

# MAGIC %md
# MAGIC ## Clean scalars + parse arrays

# COMMAND ----------

b = spark.table(f'{SCHEMA_FQN}.bronze_facilities')

f = (b
     .withColumn('facility_id', F.col('unique_id'))
     .withColumn('cluster_id', clean_null(F.col('cluster_id')))
     .withColumn('name_clean', F.initcap(F.trim(F.col('name'))))
     .withColumn('facility_type', F.lower(clean_null(F.col('facilityTypeId'))))
     .withColumn('operator_type', F.lower(clean_null(F.col('operatorTypeId'))))
     .withColumn('description', clean_null(F.col('description')))
     .withColumn('year_established', clean_null(F.col('yearEstablished')).cast('int'))
     .withColumn('capacity_beds', clean_null(F.col('capacity')).cast('int'))
     .withColumn('number_doctors', clean_null(F.col('numberDoctors')).cast('int'))
     .withColumn('city', norm_text(clean_null(F.col('address_city'))))
     .withColumn('state', norm_text(clean_null(F.col('address_stateOrRegion'))))
     .withColumn('pincode', F.regexp_extract(F.coalesce(F.col('address_zipOrPostcode'), F.lit('')), r'(\d{6})', 1))
     .withColumn('official_website', clean_null(F.col('officialWebsite')))
     .withColumn('official_phone', clean_null(F.col('officialPhone')))
     .withColumn('email', clean_null(F.col('email')))
     .withColumn('facebook_link', clean_null(F.col('facebookLink')))
     .withColumn('recency', clean_null(F.col('recency_of_page_update')))
     # JSON arrays -> deduped array<string>
     .withColumn('specialties_arr', parse_json_array(F.col('specialties')))
     .withColumn('procedure_arr', parse_json_array(F.col('procedure')))
     .withColumn('equipment_arr', parse_json_array(F.col('equipment')))
     .withColumn('capability_arr', parse_json_array(F.col('capability')))
     .withColumn('source_urls_arr', parse_json_array(F.col('source_urls')))
     .withColumn('source_types_arr', parse_json_array(F.col('source_types')))
     .withColumn('source_ids_arr', parse_json_array(F.col('source_ids')))
     .withColumn('phones_arr', parse_json_array(F.col('phone_numbers')))
     .withColumn('websites_arr', parse_json_array(F.col('websites'))))

# range-validate numerics
f = (f.withColumn('year_established', F.when(F.col('year_established').between(YEAR_MIN, YEAR_MAX), F.col('year_established')))
       .withColumn('capacity_beds', F.when(F.col('capacity_beds') > 0, F.col('capacity_beds')))
       .withColumn('number_doctors', F.when(F.col('number_doctors') > 0, F.col('number_doctors'))))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validate geography (India bbox + pincode fallback)

# COMMAND ----------

f = (f.withColumn('lat_raw', F.col('latitude').cast('double'))
       .withColumn('lon_raw', F.col('longitude').cast('double')))

p = (spark.table(f'{SCHEMA_FQN}.dim_pincode')
     .select('pincode', 'centroid_lat', 'centroid_long',
             F.col('district').alias('pin_district'),
             F.col('state').alias('pin_state')))

f = f.join(p, on='pincode', how='left')

f = (f
     .withColumn('raw_valid', is_valid_india_coord(F.col('lat_raw'), F.col('lon_raw')))
     .withColumn('latitude_clean', F.when(F.col('raw_valid'), F.col('lat_raw')).otherwise(F.col('centroid_lat')))
     .withColumn('longitude_clean', F.when(F.col('raw_valid'), F.col('lon_raw')).otherwise(F.col('centroid_long')))
     .withColumn('geo_is_valid', F.col('latitude_clean').isNotNull() & F.col('longitude_clean').isNotNull())
     .withColumn('geo_source', F.when(F.col('raw_valid'), F.lit('raw'))
                                .when(F.col('centroid_lat').isNotNull(), F.lit('pincode_fallback'))
                                .otherwise(F.lit('none')))
     .withColumn('state_mismatch', F.when(F.col('pin_state').isNotNull() & (F.col('state') != ''),
                                          F.col('pin_state') != F.col('state'))))

# COMMAND ----------

silver = f.select(
    'facility_id', 'cluster_id', 'name_clean', 'facility_type', 'operator_type',
    'description', 'year_established', 'capacity_beds', 'number_doctors',
    'city', 'state', 'pincode', 'pin_district', 'pin_state',
    'lat_raw', 'lon_raw', 'latitude_clean', 'longitude_clean',
    'geo_is_valid', 'geo_source', 'state_mismatch',
    'official_website', 'official_phone', 'email', 'facebook_link', 'recency',
    'specialties_arr', 'procedure_arr', 'equipment_arr', 'capability_arr',
    'source_urls_arr', 'source_types_arr', 'source_ids_arr', 'phones_arr', 'websites_arr')
write_table(silver, 'silver_facilities')

# COMMAND ----------

# quick data-quality read-out
s = spark.table(f'{SCHEMA_FQN}.silver_facilities')
print('rows:', s.count())
s.groupBy('geo_source').count().show()
s.select(F.round(F.avg(F.col('geo_is_valid').cast('int')), 3).alias('pct_geo_valid'),
         F.round(F.avg(F.col('state_mismatch').cast('int')), 3).alias('pct_state_mismatch')).show()
