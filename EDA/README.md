# EDA — Referral Copilot

Exploratory data analysis and data-modeling notes for the **Referral Copilot** Databricks App
(turn 10,000 messy Indian healthcare facility records into evidence-attached referral decisions).

## Contents

| Doc | Purpose |
|---|---|
| [01_data_overview.md](01_data_overview.md) | The three source files, their grain, role, and how they relate |
| [02_data_quality_issues.md](02_data_quality_issues.md) | Concrete data-quality problems found in the sample (with evidence) |
| [03_cleaning_route.md](03_cleaning_route.md) | Bronze → Silver → Gold cleaning route (Medallion) |
| [04_schema_and_erd.md](04_schema_and_erd.md) | Target schema + Mermaid ERD |

## Source data

All raw samples live in [../sample_data/raw_data](../sample_data/raw_data):

- `facilities_100.csv` — 100-row sample of the 10,000 facility records (51 columns)
- `india_post_pincode_directory_100.csv` — pincode → district/state + lat/long reference
- `nfhs_5_district_health_indicators_100.csv` — district-level public-health context (NFHS-5)

## TL;DR

1. **Everything is a string**, arrays are JSON-encoded text, and `"null"` / `"NA"` are literal strings — not real NULLs.
2. **Coordinates can be wrong** (e.g. a Kerala facility plotted in the North Atlantic) — they need India bounding-box validation with a pincode-centroid fallback.
3. The free-text `capability` / `procedure` / `equipment` fields are **claims to verify**, not ground truth — every claim must keep its **source URL** for citation and carry a **confidence** score.
4. Target model = **Medallion** (Bronze/Silver/Gold) feeding a Gold star schema plus **user-persistence** tables for shortlists, notes, overrides, and review decisions.
