# 03 — Cleaning Route (Medallion)

Bronze → Silver → Gold on Databricks Free Edition (Delta tables / Unity Catalog).

**Each layer is its own database (schema):** Bronze → `workspace.referral_copilot_bronze`,
Silver → `workspace.referral_copilot_silver`, Gold → `workspace.referral_copilot` (the
project database, kept as the serving layer). `00_setup` exposes `BRONZE_SCHEMA_FQN`,
`SILVER_SCHEMA_FQN`, `GOLD_SCHEMA_FQN`; `write_table(df, name, schema_fqn)` routes each
table to its layer and Gold reads cross-layer from Silver where needed.

## 🥉 Bronze — raw landing

- Ingest all three CSVs **verbatim** as strings (no transforms — auditability).
- Add lineage columns: `_source_file`, `_ingest_ts`, `_row_hash`.

| Bronze table | Source |
|---|---|
| `bronze_facilities` | `facilities_*.csv` |
| `bronze_pincode` | `india_post_pincode_directory_*.csv` |
| `bronze_nfhs` | `nfhs_5_district_health_indicators_*.csv` |

## 🥈 Silver — cleaned & conformed

**Facilities**

> **🚧 Validity gate (runs first):** rows whose `unique_id` isn't a UUID — upstream
> column-shift corruption where markdown / text fragments (`**Ophthalmology**`, `--|--`,
> `… More`, `**Services:**`) landed in the id column — or that have no name are **quarantined**
> to `silver_facilities_quarantine` with a reason, not deleted. Deterministic regex, not GenAI:
> structural corruption is a rules job (free, instant, auditable).

1. **Null normalization** — `"null" | "NA" | "" | "[]"` → real `NULL`.
2. **Parse JSON arrays** → `array<string>` for phones, websites, sources, specialties, procedure, equipment, capability; **dedup** elements.
3. **Type casts** — `yearEstablished`→int (1850–2026), `capacity`/`numberDoctors`→int, lat/long→double, metrics→int, dates→date.
4. **Geo validation** — keep lat∈[6,38], long∈[68,98]; else fall back to `dim_pincode` centroid; set `geo_is_valid`, `geo_source`.
5. **Standardize geography** — trim/upper-case city & state, validate 6-digit pincode against `dim_pincode`, flag `state_mismatch`.
6. **Specialty normalization** — map raw codes to controlled `dim_specialty` (`generalMedicine→internalMedicine`, `ent→otolaryngology`, `dental→dentistry`, …).
7. **Strip NUL bytes** — remove `\u0000` from every string / `array<string>` field (`sanitize_strings`) so Silver and the Gold tables it feeds can sync to **Lakebase** (Postgres rejects `\u0000` in `text` columns and fails the whole row). Applied to `dim_pincode` and `dim_district_health` too; the one Gold table that reads Bronze directly (`facility_specialty`) strips its key inline.

**Pincode reference** → `dim_pincode`
- **Validity gate** → quarantine post-office rows with a non-6-digit pincode or missing /
  out-of-India coordinates to `dim_pincode_quarantine` (previously a silent `.filter` drop).
- Cast lat/long to double; aggregate to **one row per pincode** (centroid = avg of valid
  office coords, `office_count`).

**NFHS reference** → `dim_district_health`
- **Validity gate** → quarantine rows missing the `district_name | state_ut` join key to
  `dim_district_health_quarantine`.
- Strip `()` small-sample markers; map `*` → NULL + `is_suppressed`.
- Cast indicators to double; normalize `district_name` / `state_ut`.

| Silver table | Grain |
|---|---|
| `silver_facilities` | 1 cleaned facility |
| `dim_pincode` | 1 pincode |
| `dim_district_health` | 1 district |
| `*_quarantine` | rejected rows + `quarantine_reason` (one per cleaned table, audit) |

### Validity gate (reusable across tables)

Two shared helpers in `00_setup` let **any** table adopt the same *flag-don't-drop* pattern,
so this generalizes beyond facilities:

- `first_failure((bad_cond, "reason"), …)` → builds a `quarantine_reason` column (first
  matching rule wins; `NULL` = clean).
- `quarantine_split(df, name)` → writes the rejects to `{name}_quarantine` (audit) and
  returns the clean rows.

Each table just declares its own bad-row rules (UUID shape, valid pincode, present join key).
Deterministic checks stay **rules**; **GenAI is reserved for *semantic* checks** on the clean
survivors (e.g. “does the description actually support the claimed procedure?”) — never for
structural corruption a regex catches perfectly.

## 🥇 Gold — serving / business

1. **Deduplicate** per `cluster_id` → one **golden facility** (`dim_facility`); keep member records as supporting evidence.
2. **Explode arrays** into normalized evidence tables, each row carrying **provenance** (`source_url`, `is_official`) so the app can cite it:
   - `facility_specialty`, `facility_procedure`, `facility_equipment`, `facility_capability`, `facility_source`, `facility_contact`.
3. **Care-need mapping** — build `dim_care_need` + `bridge_care_need_specialty` so a query like "dialysis" maps to nephrology + procedure/equipment keywords.
4. **Enrich context** — facility → `dim_pincode` → district → `dim_district_health`.
5. **Confidence & evidence band** — compute transparent per-claim `confidence`
   (source authority + corroboration count across `source_ids` + recency) and a facility-level `evidence_band` (High / Medium / Low). **Show the evidence, never just the score.**
6. **Serving views** — `vw_referral_candidates` (location + need → ranked candidates with distance, matching evidence, missing/suspicious evidence).
7. **User persistence** — create tables for scenarios, shortlists, notes, overrides, review decisions.

## Confidence (transparent formula)

```
confidence = w1 * source_authority      -- official site / gov > aggregator > social
           + w2 * corroboration_count   -- distinct source_ids backing the claim
           + w3 * recency_factor         -- recency_of_page_update / last post date
```

`evidence_band = High | Medium | Low` thresholds on the facility's aggregate confidence and field coverage.

## Pipeline order

```
bronze_*  ─►  dim_pincode ─►  silver_facilities (geo fallback uses dim_pincode)
          ─►  dim_district_health
                                   │
                                   ▼
        dim_facility ─► facility_specialty / procedure / equipment / capability / source / contact
                                   │
                                   ▼
                 vw_referral_candidates  +  user_* persistence tables
```
