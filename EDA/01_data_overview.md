# 01 — Data Overview

Source files in [../sample_data/raw_data](../sample_data/raw_data).

## Files, grain, and role

| File | Grain (1 row =) | Role | Notes |
|---|---|---|---|
| `facilities_100.csv` | 1 facility (51 cols) | **Core / fact** | Messy; every column typed as `string`; arrays stored as JSON text; many literal `"null"` |
| `india_post_pincode_directory_100.csv` | 1 post office | **Geo reference** | `pincode → district/state + lat/long`; some lat/long are `NA` |
| `nfhs_5_district_health_indicators_100.csv` | 1 district | **Context reference** | ~100 health indicators; messy values (`*`, `(29.5)`, trailing spaces) |

## Facility columns (grouped)

| Group | Columns |
|---|---|
| **Identity** | `unique_id`, `name`, `organization_type`, `facilityTypeId`, `operatorTypeId`, `cluster_id` |
| **Provenance** | `source_types`, `source_ids`, `source_content_id`, `content_table_id`, `source`, `source_urls`, `websites`, `officialWebsite`, `facebookLink` |
| **Contact** | `phone_numbers`, `officialPhone`, `email` |
| **Address / geo** | `address_line1..3`, `address_city`, `address_stateOrRegion`, `address_zipOrPostcode`, `address_country`, `address_countryCode`, `countries`, `area`, `coordinates`, `latitude`, `longitude` |
| **Structured capacity** | `yearEstablished`, `numberDoctors`, `capacity` |
| **Evidence (free-text claims)** | `description`, `specialties`, `procedure`, `equipment`, `capability` |
| **Signals / metrics** | `recency_of_page_update`, `distinct_social_media_presence_count`, `affiliated_staff_presence`, `custom_logo_presence`, `number_of_facts_about_the_organization`, `post_metrics_*`, `engagement_metrics_*` |
| **Misc** | `acceptsVolunteers`, `affiliationTypeIds` |

## Field coverage (from the challenge brief)

| Field | Coverage |
|---|---|
| description | 100% |
| capability | 99.7% |
| procedure | 92.5% |
| equipment | 77.0% |
| numberDoctors | 36.4% |
| capacity | 25.2% |
| yearEstablished | 47.8% |

> Evidence fields are noisy, repetitive, and unevenly supported — treat them as **claims to verify**, not ground truth.

## How the sources relate

```
facilities.address_zipOrPostcode ──► dim_pincode.pincode ──► dim_pincode.district/state
                                                                   │
                                                                   ▼
                                              nfhs_5.district_name + state_ut  (context)
```

- Facilities join to the **pincode** directory on the 6-digit postcode to recover a trustworthy district/state and a centroid lat/long.
- The pincode district then joins to **NFHS-5** district indicators to add public-health context (e.g. institutional-birth %, health-insurance coverage) around a candidate facility.
- Join keys are messy (`address_stateOrRegion` vs `statename` vs `state_ut`; city vs `district`) and require normalization + a district crosswalk.
