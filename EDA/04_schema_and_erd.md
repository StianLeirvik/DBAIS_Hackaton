# 04 — Target Schema & ERD

Gold-layer star schema for the Referral Copilot, plus user-persistence tables.

## Table groups

| Group | Tables |
|---|---|
| **Reference / dimension** | `dim_pincode`, `dim_district_health`, `dim_specialty`, `dim_care_need`, `bridge_care_need_specialty` |
| **Core** | `dim_facility`, `facility_source` (citations), `facility_contact` |
| **Evidence (claims to verify)** | `facility_specialty`, `facility_procedure`, `facility_equipment`, `facility_capability` |
| **User persistence** | `user_scenario`, `user_shortlist`, `user_shortlist_item`, `user_note`, `user_override`, `user_review_decision` |

## Mermaid ERD

```mermaid
erDiagram
    DIM_FACILITY ||--o{ FACILITY_SOURCE        : "cited by"
    DIM_FACILITY ||--o{ FACILITY_CONTACT       : has
    DIM_FACILITY ||--o{ FACILITY_SPECIALTY     : claims
    DIM_FACILITY ||--o{ FACILITY_PROCEDURE     : claims
    DIM_FACILITY ||--o{ FACILITY_EQUIPMENT     : claims
    DIM_FACILITY ||--o{ FACILITY_CAPABILITY    : claims
    DIM_FACILITY }o--|| DIM_PINCODE            : "located in"
    DIM_PINCODE  }o--o| DIM_DISTRICT_HEALTH     : "context (via xref)"

    FACILITY_SPECIALTY }o--|| DIM_SPECIALTY     : "typed as"
    DIM_CARE_NEED ||--o{ BRIDGE_CARE_NEED_SPECIALTY : maps
    DIM_SPECIALTY ||--o{ BRIDGE_CARE_NEED_SPECIALTY : maps

    DIM_FACILITY ||--o{ USER_SHORTLIST_ITEM    : "saved in"
    USER_SHORTLIST ||--o{ USER_SHORTLIST_ITEM  : contains
    DIM_FACILITY ||--o{ USER_NOTE              : annotated
    DIM_FACILITY ||--o{ USER_OVERRIDE          : corrected
    DIM_FACILITY ||--o{ USER_REVIEW_DECISION   : reviewed
    USER_SCENARIO ||--o{ USER_SHORTLIST        : produces

    DIM_FACILITY {
        string  facility_id PK "from unique_id"
        string  cluster_id "dedup group"
        string  name_clean
        string  facility_type "hospital/clinic"
        string  operator_type "private/public"
        int     year_established "nullable"
        int     capacity_beds "nullable"
        int     number_doctors "nullable"
        string  city
        string  state
        string  pincode FK
        double  latitude_clean
        double  longitude_clean
        boolean geo_is_valid
        string  geo_source "raw|pincode_fallback"
        string  evidence_band "High|Med|Low"
        double  data_quality_score
    }
    FACILITY_SOURCE {
        string  source_pk PK
        string  facility_id FK
        string  source_url
        string  source_type "overture|dynamic.."
        boolean is_official
    }
    FACILITY_CONTACT {
        string  contact_pk PK
        string  facility_id FK
        string  channel "phone|email|web|fb"
        string  value
        boolean is_official
    }
    FACILITY_SPECIALTY {
        string  facility_id FK
        string  specialty_code FK
        int     mention_count
        double  confidence
    }
    FACILITY_PROCEDURE {
        string  facility_id FK
        string  procedure_text
        string  normalized_tag
        double  confidence
        string  evidence_source_url
    }
    FACILITY_EQUIPMENT {
        string  facility_id FK
        string  equipment_text
        string  normalized_tag
        double  confidence
    }
    FACILITY_CAPABILITY {
        string  facility_id FK
        string  capability_text
        double  confidence
        string  evidence_source_url
    }
    DIM_PINCODE {
        string  pincode PK
        string  district
        string  state
        double  centroid_lat
        double  centroid_long
        int     office_count
    }
    DIM_DISTRICT_HEALTH {
        string  district_state_key PK
        string  district_name
        string  state_ut
        double  institutional_birth_5y_pct
        double  hh_member_health_insurance_pct
        boolean has_suppressed_values
    }
    DIM_SPECIALTY {
        string  specialty_code PK
        string  display_name
        string  category
    }
    DIM_CARE_NEED {
        string  care_need PK "dialysis|emergency.."
        string  match_keywords "for proc/equip"
    }
    BRIDGE_CARE_NEED_SPECIALTY {
        string  care_need FK
        string  specialty_code FK
        double  weight
    }
    USER_SCENARIO {
        string  scenario_id PK
        string  user_id
        string  location_query
        string  care_need
        string  params_json
        timestamp created_at
    }
    USER_SHORTLIST {
        string  shortlist_id PK
        string  user_id
        string  scenario_id FK
        string  name
        timestamp created_at
    }
    USER_SHORTLIST_ITEM {
        string  shortlist_id FK
        string  facility_id FK
        int     rank
        double  distance_km
        timestamp added_at
    }
    USER_NOTE {
        string  note_id PK
        string  user_id
        string  facility_id FK
        string  note_text
        timestamp created_at
    }
    USER_OVERRIDE {
        string  override_id PK
        string  user_id
        string  facility_id FK
        string  field_name
        string  original_value
        string  override_value
        string  reason
    }
    USER_REVIEW_DECISION {
        string  review_id PK
        string  user_id
        string  facility_id FK
        string  claim_ref
        string  decision "verified|rejected|needs_info"
        timestamp created_at
    }
```

## Why this fits the Referral Copilot

- **Location + need in → ranked out** — `DIM_CARE_NEED → DIM_SPECIALTY → FACILITY_SPECIALTY`, ranked by distance from validated `latitude_clean` / `longitude_clean` (pincode fallback when raw coords fail the India bounding box).
- **Evidence attached** — each candidate joins `FACILITY_*` claim rows + `FACILITY_SOURCE` URLs for citation of every important claim.
- **Honest uncertainty** — per-claim `confidence`, facility `evidence_band`, `geo_is_valid`, and `state_mismatch` surface weak/suspicious evidence instead of hiding it.
- **Persistence** — `USER_SCENARIO / SHORTLIST / NOTE / OVERRIDE / REVIEW_DECISION` cover save, revise, and review-decision workflows.
