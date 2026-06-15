# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · Gold — evidence (claims to verify)
# MAGIC
# MAGIC Explode the free-text evidence arrays into normalized claim tables, each row carrying
# MAGIC **provenance** (a citation URL) and a transparent **confidence** score. Then roll up to a
# MAGIC facility **`evidence_band`** and merge it back into `dim_facility`.
# MAGIC
# MAGIC ### Confidence (v1 heuristic — fully tunable in `00_setup`)
# MAGIC ```
# MAGIC confidence = W_AUTHORITY     * authority      # official site present -> stronger
# MAGIC            + W_CORROBORATION * corroboration  # distinct sources, capped
# MAGIC            + W_RECENCY       * recency        # page/post recency
# MAGIC ```
# MAGIC These are **claims to verify**, never ground truth — the app shows the evidence + the score.

# COMMAND ----------

# MAGIC %run ./00_setup

# COMMAND ----------

d = spark.table(f'{SCHEMA_FQN}.dim_facility')

# facility-level confidence components
base = (d.select('facility_id', 'description', 'official_website',
                 'n_sources', 'recency', 'source_urls_arr')
        .withColumn('authority', F.when(F.col('official_website').isNotNull(), F.lit(1.0)).otherwise(F.lit(0.6)))
        .withColumn('corroboration', F.least(F.col('n_sources') / F.lit(float(CORROBORATION_CAP)), F.lit(1.0)))
        .withColumn('recency_score', F.when(F.col('recency').rlike(r'202[4-9]'), F.lit(1.0))
                                      .when(F.col('recency').isNotNull(), F.lit(0.6))
                                      .otherwise(F.lit(0.3)))
        .withColumn('confidence', F.round(
            F.lit(W_AUTHORITY) * F.col('authority') +
            F.lit(W_CORROBORATION) * F.col('corroboration') +
            F.lit(W_RECENCY) * F.col('recency_score'), 3))
        .withColumn('primary_citation', F.coalesce(F.col('official_website'),
                                                   F.element_at(F.col('source_urls_arr'), 1))))

conf = base.select('facility_id', 'confidence', 'primary_citation')

# COMMAND ----------

# Per-facility signals + keyword sets for each evidence field (used for cross-field corroboration).
def _field_kw(arr_col):
    return keywords(F.array_join(F.coalesce(arr_col, F.array()), ' '))

sig = (d.select('facility_id', 'official_website', 'n_sources', 'geo_is_valid',
                'procedure_arr', 'equipment_arr', 'capability_arr', 'specialties_arr')
        .withColumn('has_official', F.col('official_website').isNotNull())
        .withColumn('kw_procedure', _field_kw(F.col('procedure_arr')))
        .withColumn('kw_equipment', _field_kw(F.col('equipment_arr')))
        .withColumn('kw_capability', _field_kw(F.col('capability_arr')))
        .withColumn('kw_specialty', _field_kw(F.col('specialties_arr'))))

def explode_evidence(field_col, text_name, table_name, support_cols):
    '''Explode one evidence array into a claim table tagged Reliable/Uncertain/Unreliable.
    `support_cols` = the OTHER fields' keyword sets that can corroborate this claim.'''
    support = F.array_distinct(F.concat(*[F.coalesce(F.col(c), F.array()) for c in support_cols]))
    ev = (sig
          .withColumn(text_name, F.explode(F.col(field_col)))
          .withColumn('normalized_tag', F.lower(F.trim(F.col(text_name))))
          .withColumn('corroborating_terms', F.array_intersect(keywords(F.col(text_name)), support))
          .join(conf, 'facility_id', 'left'))
    is_rel, rel, reason = reliability_expr(F.col('has_official'), F.col('n_sources'),
                                           F.col('corroborating_terms'), F.col('geo_is_valid'))
    ev = (ev.withColumn('is_reliable', is_rel)
            .withColumn('reliability', rel)
            .withColumn('reliability_reason', reason)
            .withColumnRenamed('primary_citation', 'evidence_source_url')
            .select('facility_id', text_name, 'normalized_tag', 'confidence',
                    'corroborating_terms', 'is_reliable', 'reliability',
                    'reliability_reason', 'evidence_source_url'))
    write_table(ev, table_name)

# procedure is the key "can they actually do it?" claim -> corroborate with equipment/specialty/capability
explode_evidence('procedure_arr', 'procedure_text', 'facility_procedure',
                 ['kw_equipment', 'kw_capability', 'kw_specialty'])
explode_evidence('equipment_arr', 'equipment_text', 'facility_equipment',
                 ['kw_procedure', 'kw_capability', 'kw_specialty'])
explode_evidence('capability_arr', 'capability_text', 'facility_capability',
                 ['kw_procedure', 'kw_equipment', 'kw_specialty'])

# COMMAND ----------

# facility_specialty keeps a real mention_count from the *raw* (non-deduped) bronze arrays,
# mapped from cluster member ids up to the golden facility_id.
member_map = d.select('facility_id', F.explode('member_ids').alias('unique_id'))
bron = spark.table(f'{BRONZE_SCHEMA_FQN}.bronze_facilities').select('unique_id', 'specialties')

raw_spec = (bron.join(member_map, 'unique_id', 'inner')
            .withColumn('code', F.explode(F.from_json(F.col('specialties'), ArrayType(StringType()))))
            .filter(F.col('code').isNotNull() & (F.trim(F.col('code')) != '')))

fac_spec = (raw_spec.groupBy('facility_id', F.lower(F.trim(F.col('code'))).alias('specialty_code'))
            .agg(F.count('*').alias('mention_count'))
            .join(conf.select('facility_id', 'confidence'), 'facility_id', 'left'))
write_table(fac_spec, 'facility_specialty')

# COMMAND ----------

# facility_source — citations (is_official when the url matches the official website domain)
fac_source = (d.select('facility_id', 'official_website', F.explode('source_urls_arr').alias('source_url'))
              .withColumn('is_official', F.when(F.col('official_website').isNotNull() &
                          F.col('source_url').contains(F.regexp_replace(F.col('official_website'), r'^https?://', '')), True)
                          .otherwise(False))
              .drop('official_website'))
write_table(fac_source, 'facility_source')

# facility_contact — one row per channel/value
phones   = d.select('facility_id', F.explode('phones_arr').alias('value')).withColumn('channel', F.lit('phone')).withColumn('is_official', F.lit(False))
off_ph   = d.where(F.col('official_phone').isNotNull()).select('facility_id', F.col('official_phone').alias('value')).withColumn('channel', F.lit('phone')).withColumn('is_official', F.lit(True))
emails   = d.where(F.col('email').isNotNull()).select('facility_id', F.col('email').alias('value')).withColumn('channel', F.lit('email')).withColumn('is_official', F.lit(True))
webs     = d.select('facility_id', F.explode('websites_arr').alias('value')).withColumn('channel', F.lit('web')).withColumn('is_official', F.lit(False))
fb       = d.where(F.col('facebook_link').isNotNull()).select('facility_id', F.col('facebook_link').alias('value')).withColumn('channel', F.lit('facebook')).withColumn('is_official', F.lit(False))
contacts = (phones.unionByName(off_ph).unionByName(emails).unionByName(webs).unionByName(fb)
            .dropDuplicates(['facility_id', 'channel', 'value']))
write_table(contacts, 'facility_contact')

# COMMAND ----------

# Roll up to a facility evidence band, then MERGE it into dim_facility.
summary = (base.select('facility_id', 'confidence', 'n_sources')
           .join(d.select('facility_id', 'n_capability'), 'facility_id', 'left')
           .withColumn('evidence_strength', F.col('confidence'))
           .withColumn('evidence_band',
                F.when((F.col('confidence') >= 0.7) & (F.col('n_sources') >= 2) & (F.col('n_capability') >= 3), F.lit('High'))
                 .when((F.col('confidence') >= 0.5) & (F.col('n_sources') >= 1), F.lit('Medium'))
                 .otherwise(F.lit('Low'))))
write_table(summary.select('facility_id', 'evidence_strength', 'evidence_band', 'confidence', 'n_sources'),
            'facility_evidence_summary')

spark.sql(f'''
MERGE INTO {SCHEMA_FQN}.dim_facility AS t
USING {SCHEMA_FQN}.facility_evidence_summary AS s
ON t.facility_id = s.facility_id
WHEN MATCHED THEN UPDATE SET
  t.evidence_band = s.evidence_band,
  t.evidence_strength = s.evidence_strength
''')
print('evidence bands merged into dim_facility')
spark.table(f'{SCHEMA_FQN}.dim_facility').groupBy('evidence_band').count().show()

# COMMAND ----------

# Reliability read-out for procedure claims (can the facility actually perform it?)
fp = spark.table(f'{SCHEMA_FQN}.facility_procedure')
fp.groupBy('reliability').count().orderBy(F.desc('count')).show()
print('Sample reliable vs unreliable procedure claims:')
(fp.select('procedure_text', 'reliability', 'reliability_reason')
   .orderBy(F.desc('is_reliable')).show(8, truncate=80))
