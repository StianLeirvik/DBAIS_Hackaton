# Databricks notebook source
# MAGIC %md
# MAGIC # 07 · Gold — serving layer
# MAGIC
# MAGIC What the Referral Copilot app calls at runtime:
# MAGIC
# MAGIC - **`vw_facility_enriched`** — `dim_facility` + evidence band + NFHS district context.
# MAGIC - **`search_referrals(location, care_need)`** — *location + need in → ranked candidates out*,
# MAGIC   each with distance, matching evidence, missing/suspicious-evidence flags, and citations.
# MAGIC   Every candidate also shows whether the matched **procedure claim is Reliable/Unreliable**
# MAGIC   and *why* (`match_reliability` + `match_reliability_reason`), and reliable matches rank first.

# COMMAND ----------

# MAGIC %run ./00_setup

# COMMAND ----------

spark.sql(f'''
CREATE OR REPLACE VIEW {SCHEMA_FQN}.vw_facility_enriched AS
SELECT
  f.facility_id, f.name_clean, f.facility_type, f.operator_type,
  f.city, f.state, f.pincode, f.pin_district,
  f.latitude_clean, f.longitude_clean, f.geo_is_valid, f.geo_source, f.state_mismatch,
  f.year_established, f.capacity_beds, f.number_doctors,
  f.specialties_arr, f.procedure_arr, f.equipment_arr, f.capability_arr,
  f.source_urls_arr, f.official_website,
  f.data_quality_score, f.evidence_band, f.evidence_strength,
  h.institutional_birth_5y_pct, h.hh_health_insurance_pct, h.has_suppressed_values
FROM {SCHEMA_FQN}.dim_facility f
LEFT JOIN {SCHEMA_FQN}.dim_district_health h
  ON f.pin_district = h.district_name AND f.state = h.state_ut
''')
print('vw_facility_enriched created')

# COMMAND ----------

from pyspark.sql import functions as F

def resolve_location(query):
    '''Resolve a 6-digit pincode or a place name to (lat, lon, label).
    Tries dim_pincode first, then falls back to facility coordinates.'''
    q = str(query).strip().upper()
    pin = spark.table(f'{SCHEMA_FQN}.dim_pincode')

    if q.isdigit() and len(q) == 6:
        r = pin.where(F.col('pincode') == q).agg(
                F.avg('centroid_lat').alias('lat'), F.avg('centroid_long').alias('lon'),
                F.first('district').alias('label')).first()
        if r['lat'] is not None:
            return (r['lat'], r['lon'], r['label'])

    r = pin.where(F.col('district').contains(q)).agg(
            F.avg('centroid_lat').alias('lat'), F.avg('centroid_long').alias('lon'),
            F.first('district').alias('label')).first()
    if r['lat'] is not None:
        return (r['lat'], r['lon'], r['label'])

    fac = spark.table(f'{SCHEMA_FQN}.dim_facility').where(F.col('geo_is_valid'))
    r = (fac.where(F.col('city').contains(q) | F.col('pin_district').contains(q) | F.col('state').contains(q))
            .agg(F.avg('latitude_clean').alias('lat'), F.avg('longitude_clean').alias('lon'),
                 F.first('city').alias('label')).first())
    if r['lat'] is not None:
        return (r['lat'], r['lon'], r['label'])
    return None

# COMMAND ----------

def search_referrals(location, care_need, top_n=10, max_km=150):
    '''location + care_need -> ranked candidate facilities with attached evidence.'''
    loc = resolve_location(location)
    if loc is None:
        print('Could not resolve location:', location)
        return None
    lat, lon, label = loc
    print(f'Searching near {label} ({lat:.3f}, {lon:.3f}) for "{care_need}"')

    # expand care need -> specialties + keywords
    cn = spark.table(f'{SCHEMA_FQN}.dim_care_need').where(F.col('care_need') == care_need).first()
    keywords = list(cn['match_keywords']) if cn else [care_need]
    specs = [r['specialty_code'] for r in
             spark.table(f'{SCHEMA_FQN}.bridge_care_need_specialty')
                  .where(F.col('care_need') == care_need).collect()]
    kw_regex = '(?i)(' + '|'.join([k.replace(' ', '.*') for k in keywords]) + ')'

    f = spark.table(f'{SCHEMA_FQN}.vw_facility_enriched').where(F.col('geo_is_valid'))
    all_ev = F.concat(F.coalesce('procedure_arr', F.array()),
                      F.coalesce('equipment_arr', F.array()),
                      F.coalesce('capability_arr', F.array()))
    spec_match = (F.arrays_overlap(F.col('specialties_arr'), F.array(*[F.lit(s) for s in specs]))
                  if specs else F.lit(False))

    f = (f
         .withColumn('distance_km', F.round(haversine_km(F.lit(lat), F.lit(lon),
                                                         F.col('latitude_clean'), F.col('longitude_clean')), 1))
         .withColumn('specialty_match', spec_match)
         .withColumn('matching_evidence', F.filter(all_ev, lambda x: x.rlike(kw_regex)))
         .withColumn('keyword_match', F.size(F.col('matching_evidence')) > 0)
         .withColumn('match_score', F.col('specialty_match').cast('int') * 2 + F.col('keyword_match').cast('int'))
         # honesty: surface weak / suspicious evidence instead of hiding it
         .withColumn('missing_evidence', F.when(F.size(F.col('matching_evidence')) == 0,
                                                F.lit('no matching procedure/equipment text')))
         .withColumn('suspicious_evidence', F.concat_ws('; ',
                     F.when(F.col('geo_source') != 'raw', F.lit('coords estimated from pincode')),
                     F.when(F.col('state_mismatch'), F.lit('address state != pincode state')),
                     F.when(F.col('evidence_band') == 'Low', F.lit('low overall evidence'))))
         .where((F.col('distance_km') <= max_km) & (F.col('match_score') > 0)))

    # Attach the reliability of the matched procedure claim: can they actually perform it?
    from pyspark.sql.window import Window
    pw = Window.partitionBy('facility_id').orderBy(F.desc('is_reliable'), F.desc('confidence'))
    proc = (spark.table(f'{SCHEMA_FQN}.facility_procedure')
            .where(F.col('procedure_text').rlike(kw_regex))
            .withColumn('_rn', F.row_number().over(pw))
            .where(F.col('_rn') == 1)
            .select('facility_id',
                    F.col('is_reliable').alias('match_is_reliable'),
                    F.col('reliability').alias('match_reliability'),
                    F.col('procedure_text').alias('match_procedure'),
                    F.col('reliability_reason').alias('match_reliability_reason')))
    f = (f.join(proc, 'facility_id', 'left')
          .withColumn('claim_warning',
                F.when(~F.coalesce(F.col('match_is_reliable'), F.lit(False)),
                       F.concat(F.lit('procedure claim is '),
                                F.coalesce(F.col('match_reliability'), F.lit('unverified')),
                                F.lit(' — '),
                                F.coalesce(F.col('match_reliability_reason'), F.lit('weak evidence'))))))

    return (f.orderBy(F.desc('match_score'),
                      F.desc(F.coalesce(F.col('match_is_reliable').cast('int'), F.lit(0))),
                      F.desc('evidence_strength'), F.asc('distance_km'))
             .limit(top_n)
             .select('facility_id', 'name_clean', 'city', 'state', 'distance_km',
                     'match_reliability', 'match_procedure', 'match_reliability_reason',
                     'evidence_band', 'evidence_strength', 'data_quality_score',
                     'specialty_match', 'matching_evidence',
                     'missing_evidence', 'suspicious_evidence', 'claim_warning',
                     'source_urls_arr', 'official_website'))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Demo
# MAGIC Try a need the sample supports. Replace with `dialysis near Jaipur` etc. once the full pincode directory is loaded.

# COMMAND ----------

res = search_referrals('AHMEDABAD', 'orthopedics', top_n=5)
if res is not None:
    res.show(truncate=60, vertical=True)
