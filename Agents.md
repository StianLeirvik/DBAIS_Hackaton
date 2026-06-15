# Intro
We are submitting a solution for a hackathon 

# The challenge
Build a Databricks App that turns messy healthcare facility data into decisions a non-technical planner can trust. Read the full prompt, dataset overview, and the four tracks below.

# Prompt
You are given 10,000 messy records of healthcare facilities across India. Each record includes structured fields such as location and specialties, plus uneven free-text descriptions of claimed capabilities, procedures, equipment, and services.

Build a Databricks App that helps a non-technical healthcare planner, NGO coordinator, or analyst turn this messy data into decisions they can trust.

Your app should extract useful structure from the records, show evidence for its conclusions, communicate uncertainty honestly, and let users save or revise their work.

# Core Requirements
Your submission must:

- Run as a Databricks App on Free Edition.
- Use the provided facility dataset.
- Support a clear non-technical user workflow.
- Cite the underlying facility text for any important claim, recommendation, score, or ranking.
- Communicate uncertainty instead of presenting weak evidence as fact.
- Persist user actions such as notes, overrides, shortlists, scenarios, or review decisions.

# Dataset
The provided dataset contains 10,000 Indian healthcare facility records and 51 columns.

All records include facility name, state, city, latitude, longitude, controlled specialties, a description, and source URLs; 9,996 records include a postcode. The extracted evidence fields are noisy, repetitive, and unevenly supported:

| Field |	Coverage |
|--|--| 
|description|	100%|
|capability|	99.7%|
|procedure|	92.5%|
|equipment|	77.0%|
|numberDoctors|	36.4%|
|capacity|	25.2%|
|yearEstablished|	47.8%|


Useful evidence appears across description, capability, procedure, equipment, specialties, and source_urls. Teams should treat these fields as claims to verify rather than ground truth.

There is sample data for the saw data in sample_data/raw_data/*.csv


# What we are creating:

##  Referral Copilot
Question: Where should a patient or coordinator actually go?

Build an app where a user enters a location and a care need, such as "dialysis near Jaipur" or "emergency surgery near Patna," and receives an evidence-attached shortlist of candidate facilities.

Minimum workflow: location and need in; ranked candidates out; each candidate shows distance, matching evidence, missing or suspicious evidence, and can be saved to a shortlist.