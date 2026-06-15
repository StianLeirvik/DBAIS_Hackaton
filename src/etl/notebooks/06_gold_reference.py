# Databricks notebook source
# MAGIC %md
# MAGIC # 06 · Gold — reference vocabularies
# MAGIC
# MAGIC Controlled vocabularies that power the care-need → specialty matching:
# MAGIC
# MAGIC - **`dim_specialty`** — canonical specialties + `aliases` (folds the mixed taxonomy, e.g. `ent`→`otolaryngology`).
# MAGIC - **`dim_care_need`** — user-facing needs + free-text `match_keywords` for procedure/equipment search.
# MAGIC - **`bridge_care_need_specialty`** — weighted care-need → specialty mapping.
# MAGIC
# MAGIC Rows are defined inline here (the single source of truth). Each table gets an
# MAGIC informational PRIMARY KEY; the bridge carries FKs to both dims.

# COMMAND ----------

# MAGIC %run ./00_setup

# COMMAND ----------

specialty_rows = [
    ('nephrology', 'Nephrology', 'medical', ['nephrology', 'dialysis', 'nephrologyanddialysis']),
    ('cardiology', 'Cardiology', 'medical', ['cardiology']),
    ('emergencyMedicine', 'Emergency Medicine', 'medical', ['emergencymedicine', 'emergency', 'casualty']),
    ('generalSurgery', 'General Surgery', 'surgical', ['generalsurgery', 'surgery']),
    ('orthopedicSurgery', 'Orthopedic Surgery', 'surgical', ['orthopedicsurgery', 'orthopedics', 'ortho']),
    ('obstetricsGynecology', 'Obstetrics & Gynecology', 'medical', ['gynecologyandobstetrics', 'obstetrics', 'gynecology', 'maternity']),
    ('pediatrics', 'Pediatrics', 'medical', ['pediatrics', 'paediatrics', 'neonatology', 'neonatologyperinatalmedicine']),
    ('oncology', 'Oncology', 'medical', ['oncology', 'cancer', 'medicaloncology']),
    ('internalMedicine', 'Internal Medicine', 'medical', ['internalmedicine', 'generalmedicine', 'medicine']),
    ('otolaryngology', 'ENT', 'surgical', ['otolaryngology', 'ent']),
    ('ophthalmology', 'Ophthalmology', 'surgical', ['ophthalmology', 'eye']),
    ('dentistry', 'Dentistry', 'medical', ['dentistry', 'dental']),
    ('radiology', 'Radiology', 'diagnostic', ['radiology', 'imaging']),
    ('neurology', 'Neurology', 'medical', ['neurology']),
    ('neurosurgery', 'Neurosurgery', 'surgical', ['neurosurgery', 'spineneurosurgery']),
    ('urology', 'Urology', 'surgical', ['urology']),
    ('gastroenterology', 'Gastroenterology', 'medical', ['gastroenterology']),
    ('pulmonology', 'Pulmonology', 'medical', ['pulmonology']),
    ('dermatology', 'Dermatology', 'medical', ['dermatology']),
    ('psychiatry', 'Psychiatry', 'medical', ['psychiatry']),
]
dim_specialty = spark.createDataFrame(specialty_rows, ['specialty_code', 'display_name', 'category', 'aliases'])
# bridge (below) carries FKs to these dims; drop them first so the overwrite is allowed.
drop_all_fks()
write_table(dim_specialty, 'dim_specialty')
add_pk('dim_specialty', 'specialty_code', rely=True)

# COMMAND ----------

care_need_rows = [
    ('dialysis', 'Dialysis', ['dialysis', 'haemodialysis', 'hemodialysis', 'renal']),
    ('emergency_surgery', 'Emergency Surgery', ['emergency', 'trauma', 'casualty', 'icu', 'operation theater']),
    ('maternity', 'Maternity / Childbirth', ['delivery', 'obstetric', 'nicu', 'caesarean', 'labour']),
    ('cardiac_care', 'Cardiac Care', ['cardiology', 'ecg', 'cath lab', 'angiography', 'heart']),
    ('cancer_care', 'Cancer Care', ['oncology', 'chemotherapy', 'radiotherapy', 'tumor']),
    ('orthopedics', 'Orthopedics / Fractures', ['fracture', 'joint replacement', 'knee', 'hip', 'spine']),
    ('pediatric_care', 'Pediatric Care', ['pediatric', 'child', 'neonatal', 'vaccination']),
    ('eye_care', 'Eye Care', ['cataract', 'eye', 'ophthalmology', 'glaucoma']),
    ('dental_care', 'Dental Care', ['dental', 'tooth', 'oral']),
    ('general_consultation', 'General Consultation', ['consultation', 'checkup', 'opd', 'general medicine']),
]
dim_care_need = spark.createDataFrame(care_need_rows, ['care_need', 'display_name', 'match_keywords'])
write_table(dim_care_need, 'dim_care_need')
add_pk('dim_care_need', 'care_need', rely=True)

bridge_rows = [
    ('dialysis', 'nephrology', 1.0), ('dialysis', 'internalMedicine', 0.4),
    ('emergency_surgery', 'emergencyMedicine', 1.0), ('emergency_surgery', 'generalSurgery', 0.9),
    ('emergency_surgery', 'orthopedicSurgery', 0.5),
    ('maternity', 'obstetricsGynecology', 1.0), ('maternity', 'pediatrics', 0.6),
    ('cardiac_care', 'cardiology', 1.0), ('cardiac_care', 'emergencyMedicine', 0.3),
    ('cancer_care', 'oncology', 1.0),
    ('orthopedics', 'orthopedicSurgery', 1.0), ('orthopedics', 'generalSurgery', 0.4),
    ('pediatric_care', 'pediatrics', 1.0),
    ('eye_care', 'ophthalmology', 1.0),
    ('dental_care', 'dentistry', 1.0),
    ('general_consultation', 'internalMedicine', 1.0),
]
bridge = spark.createDataFrame(bridge_rows, ['care_need', 'specialty_code', 'weight'])
write_table(bridge, 'bridge_care_need_specialty')
add_pk('bridge_care_need_specialty', ['care_need', 'specialty_code'], rely=True)
add_fk('bridge_care_need_specialty', 'fk_bridge_care_need', 'care_need',
       f'{GOLD_SCHEMA_FQN}.dim_care_need', 'care_need')
add_fk('bridge_care_need_specialty', 'fk_bridge_specialty', 'specialty_code',
       f'{GOLD_SCHEMA_FQN}.dim_specialty', 'specialty_code')
