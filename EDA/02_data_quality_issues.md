# 02 — Data Quality Issues

Concrete problems found in the 100-row sample, with evidence and the fix applied in Silver/Gold.

| # | Issue | Evidence (from sample) | Fix |
|---|---|---|---|
| 1 | **Literal `"null"` / `"NA"` strings** instead of real NULLs | Row 1 `yearEstablished=null`, `numberDoctors=null`, `capacity=null`; pincode lat/long `NA` | Normalize `"null"`, `"NA"`, `""`, `"[]"` → real `NULL` |
| 2 | **JSON-encoded arrays in text columns** | `phone_numbers`, `websites`, `source_types`, `source_ids`, `source_urls`, `specialties`, `procedure`, `equipment`, `capability` are stringified JSON arrays | Parse to `array<string>` |
| 3 | **Duplicates inside arrays** | `specialties` repeats `internalMedicine` 10+ times | Dedup array elements |
| 4 | **Mixed taxonomies** | `generalMedicine` vs `internalMedicine`; `ent` vs `otolaryngology`; `dental` vs `dentistry` | Map to a controlled `dim_specialty` vocabulary |
| 5 | **Broken coordinates** | Sanjivani Hospital is addressed in **Kerala / pincode 690509** but `latitude=59.95, longitude=-38.26` (North Atlantic) | India bounding-box check (lat 6–38, long 68–98); fall back to pincode centroid; record `geo_is_valid`, `geo_source` |
| 6 | **Everything stored as `string`** | `capacity`, `numberDoctors`, `yearEstablished`, engagement metrics, dates | Cast to int/double/date with range validation |
| 7 | **Claims, not facts** | `capability` lists marketing-style assertions of uneven support | Keep source URL per claim; compute confidence; never present weak evidence as fact |
| 8 | **Duplicate facilities** | `cluster_id` groups records that refer to the same facility | Resolve to one golden record per `cluster_id`; keep members as evidence |
| 9 | **Unmatched join keys** | `address_stateOrRegion` / city vs pincode `statename` / `district` vs NFHS `state_ut` / `district_name` | Trim/upper-case, validate pincode, build district crosswalk, flag `state_mismatch` |
| 10 | **NFHS suppressed / flagged values** | `*` = unavailable; `(29.5)` = small-sample flag; trailing spaces | Strip `()`, map `*` → NULL + `is_suppressed` flag, cast to double |

## Validation ranges (Silver)

| Field | Rule |
|---|---|
| `latitude` | India: `6.0 ≤ lat ≤ 38.0` else invalid → pincode fallback |
| `longitude` | India: `68.0 ≤ long ≤ 98.0` else invalid → pincode fallback |
| `yearEstablished` | `1850 ≤ year ≤ 2026` else NULL |
| `capacity_beds` | `> 0` else NULL |
| `number_doctors` | `> 0` else NULL |
| `pincode` | exactly 6 digits; must exist in `dim_pincode` |

## Honesty / uncertainty signals to surface in the app

- `geo_is_valid`, `geo_source` (raw vs pincode-fallback)
- `state_mismatch` (address state ≠ pincode state)
- per-claim `confidence` (source authority × corroboration count × recency)
- facility `evidence_band` (High / Medium / Low)
- `is_suppressed` on NFHS context values
