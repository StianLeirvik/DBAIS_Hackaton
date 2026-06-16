# CareMap

A referral-matching tool for healthcare facilities across India. Enter a location and a care need — get a ranked shortlist with transparent match scores and cited evidence.

## How the map works

Every facility marker is placed at its real `latitude_clean` / `longitude_clean` coordinates from `dim_facility`. The search-centre pin and 300 km ring are determined by a tiered geocoding cascade:

1. **PIN code input** (numeric) — looked up directly in `dim_pincode` for a precise post-office centroid.
2. **City / district name** — resolved server-side via `/api/geocode-city` using **median** coordinates (outlier-resistant):
   - **Tier 1:** Median of `centroid_lat` / `centroid_long` from `dim_pincode` where `district` matches (165k postal records — purpose-built geographic reference).
   - **Tier 2:** Median of `dim_facility` coords where `city` matches exactly.
   - **Tier 3:** Median of `dim_facility` coords where `pin_district` matches exactly.
   - **Tier 4:** LIKE fallback on city / pin_district.
   - Each tier requires ≥ 3 matching records to be accepted.
3. **Fallback** — if no tier resolves, the centroid of the returned result set is used client-side.

The 300 km ring is purely illustrative — it matches the proximity-score horizon in the ranking model. All distances are straight-line (Haversine), not travel time.

## Scoring model (max 90)

| Component | Max | Source field |
|---|---|---|
| Capability match | 45 | `specialties`, `procedures`, `equipment`, `capabilities` |
| Travel proximity | 30 | `latitude_clean` / `longitude_clean` |
| Data freshness | 15 | `evidence_band` |
| Risk penalty | −variable | coral + amber evidence flags |

## Stack

Vue 3 + TypeScript + Vite frontend · Express + PostgreSQL backend · Leaflet maps · Deployed as a Databricks App.
