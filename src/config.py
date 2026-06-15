"""Central configuration for the Referral Copilot data pipeline.

Importable by the Databricks App layer so the UI and the notebooks agree on table
names and tunable constants. The notebooks mirror these values in ``00_setup`` so they
can be loaded with ``%run ./00_setup`` without importing this module.
"""

# ----- Catalog / schema -----
CATALOG = "workspace"                 # Free Edition default catalog
SCHEMA = "referral_copilot"           # all bronze/silver/gold tables live here
SCHEMA_FQN = f"{CATALOG}.{SCHEMA}"

# ----- Source data (read-only Unity Catalog tables, provided by the hackathon) -----
# All three raw sources already exist as Unity Catalog tables; the Bronze layer reads
# them directly with spark.table(...). There is no CSV upload step.
SOURCE_CATALOG = "databricks_virtue_foundation_dataset_dais_2026"
SOURCE_SCHEMA = "virtue_foundation_dataset"
SOURCE_SCHEMA_FQN = f"{SOURCE_CATALOG}.{SOURCE_SCHEMA}"
SOURCE_FACILITIES_TABLE = f"{SOURCE_SCHEMA_FQN}.facilities"
SOURCE_PINCODE_TABLE = f"{SOURCE_SCHEMA_FQN}.india_post_pincode_directory"
SOURCE_NFHS_TABLE = f"{SOURCE_SCHEMA_FQN}.nfhs_5_district_health_indicators"

# ----- Validation constants -----
INDIA_LAT_MIN, INDIA_LAT_MAX = 6.0, 38.0
INDIA_LON_MIN, INDIA_LON_MAX = 68.0, 98.0
YEAR_MIN, YEAR_MAX = 1850, 2026

# ----- Confidence weights (transparent + tunable) -----
W_AUTHORITY, W_CORROBORATION, W_RECENCY = 0.5, 0.3, 0.2
CORROBORATION_CAP = 3                 # diminishing returns past 3 corroborating sources

# ----- Gold table names (what the app reads) -----
T_FACILITY = f"{SCHEMA_FQN}.dim_facility"
T_FACILITY_SPECIALTY = f"{SCHEMA_FQN}.facility_specialty"
T_FACILITY_PROCEDURE = f"{SCHEMA_FQN}.facility_procedure"
T_FACILITY_EQUIPMENT = f"{SCHEMA_FQN}.facility_equipment"
T_FACILITY_CAPABILITY = f"{SCHEMA_FQN}.facility_capability"
T_FACILITY_SOURCE = f"{SCHEMA_FQN}.facility_source"
T_FACILITY_CONTACT = f"{SCHEMA_FQN}.facility_contact"
T_PINCODE = f"{SCHEMA_FQN}.dim_pincode"
T_DISTRICT_HEALTH = f"{SCHEMA_FQN}.dim_district_health"
T_SPECIALTY = f"{SCHEMA_FQN}.dim_specialty"
T_CARE_NEED = f"{SCHEMA_FQN}.dim_care_need"
T_BRIDGE = f"{SCHEMA_FQN}.bridge_care_need_specialty"
VW_ENRICHED = f"{SCHEMA_FQN}.vw_facility_enriched"

# ----- User persistence tables -----
T_USER_SCENARIO = f"{SCHEMA_FQN}.user_scenario"
T_USER_SHORTLIST = f"{SCHEMA_FQN}.user_shortlist"
T_USER_SHORTLIST_ITEM = f"{SCHEMA_FQN}.user_shortlist_item"
T_USER_NOTE = f"{SCHEMA_FQN}.user_note"
T_USER_OVERRIDE = f"{SCHEMA_FQN}.user_override"
T_USER_REVIEW_DECISION = f"{SCHEMA_FQN}.user_review_decision"
