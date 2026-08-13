# Dataset Creation and Preparation Document

This document explains how the healthcare allergy dataset used by the RAG
question-answering application was selected, prepared, reduced for local demo
use, joined across tables, and indexed into ChromaDB. It is intended to provide
enough detail for project submission and for another developer or evaluator to
recreate the same dataset preparation flow.

The application is a Retrieval-Augmented Generation (RAG) demo focused on
clinical allergy questions. Instead of indexing every available healthcare table,
the project uses patient demographic records and allergy event records. This
keeps the demo clinically meaningful while keeping the retrieval scope clear and
manageable.

## 1. Source Dataset

The source dataset is:

```text
richardyoung/synthea-575k-patients
```

Source data folder:

```text
https://huggingface.co/datasets/richardyoung/synthea-575k-patients/tree/main/data
```

Dataset card:

```text
https://huggingface.co/datasets/richardyoung/synthea-575k-patients
```

The dataset is generated with Synthea and contains fully synthetic electronic
health record data. It does not contain real patient records.

Synthea is an open-source synthetic patient generator. It creates realistic but
fictional patient histories, demographics, encounters, conditions, medications,
allergies, procedures, observations, and related clinical records. This makes it
suitable for educational and demonstration projects because it allows realistic
healthcare workflows without using protected health information from real
patients.

This project uses the Synthea dataset because:

- it is large enough to demonstrate retrieval over realistic healthcare records;
- it contains structured relational clinical data;
- it avoids real patient privacy risks;
- it includes allergy records with reactions and severities, which are useful
  for clinical question-answering examples;
- it supports guardrail demonstrations involving retrieval, filtering, and
  privacy-aware output handling.

The upstream Hugging Face dataset stores clinical tables as Parquet files,
including:

- `patients.parquet`
- `allergies.parquet`
- `conditions.parquet`
- `medications.parquet`
- `encounters.parquet`
- `procedures.parquet`
- `observations.parquet`
- `immunizations.parquet`
- `careplans.parquet`

This project currently uses only the patient demographic table and the allergy
event table.

The other tables are not used in the current version because the project scope
is intentionally limited to allergy-focused RAG. Adding conditions, medications,
encounters, procedures, or observations later would be possible, but it would
also require additional indexing rules, prompt instructions, and guardrail
examples.

## 2. Local Files

The full local CSV files are:

```text
LLM-App/data/patients.csv
LLM-App/data/allergies.csv
```

The fast demo CSV files are:

```text
LLM-App/data/patients_demo.csv
LLM-App/data/allergies_demo.csv
```

The app defaults to the demo CSV files so local startup and Chroma ingestion are
fast enough for repeat demos.

The full dataset is useful for scale testing, but it is too large for quick
development and repeated demonstrations. Ingesting hundreds of thousands of
records into a vector database can take noticeable time, especially when the
backend is restarted frequently. For this reason, the project keeps both the
full files and a smaller demo subset.

The demo subset is the default because it provides:

- faster backend startup;
- faster Chroma collection rebuilds;
- enough allergy examples for meaningful retrieval;
- simpler and more reliable project demonstrations;
- lower local disk and compute overhead during testing.

Current intended row counts:

| File | Data Rows | Purpose |
| --- | ---: | --- |
| `patients.csv` | 575,415 | Full patient table |
| `allergies.csv` | 529,829 | Full allergy table |
| `patients_demo.csv` | 7,000 | 6,745 patients referenced by the sampled allergies + 255 filler patients |
| `allergies_demo.csv` | 7,000 | Category-balanced sampled allergy events (food / environment / medication) |

## 3. Converting From Hugging Face Parquet To CSV

If the local CSVs need to be regenerated from Hugging Face, download the two
required Parquet files and convert them:

```python
import pandas as pd
from huggingface_hub import hf_hub_download

repo_id = "richardyoung/synthea-575k-patients"

for table in ["patients", "allergies"]:
    parquet_path = hf_hub_download(
        repo_id=repo_id,
        filename=f"data/{table}.parquet",
        repo_type="dataset",
    )
    df = pd.read_parquet(parquet_path)
    df.to_csv(f"LLM-App/data/{table}.csv", index=False)
```

The full upstream dataset is large. The allergy RAG demo does not need all
tables.

After conversion, the resulting CSV files are stored under `LLM-App/data/`.
These CSV files become the source-of-truth inputs for the application ingestion
pipeline.

## 4. Creating The Demo Dataset

The full CSVs are slow to ingest during local demos, so the project includes a
deterministic resize script:

```text
LLM-App/scripts/create_demo_dataset.py
```

The script samples allergy rows first, then writes only the matching patients.
This preserves the patient-allergy join while reducing ingestion time.

This order is important. If patients were sampled first, many sampled patients
may not have allergy rows, and the resulting allergy demo could become sparse.
By sampling allergy rows first, every sampled allergy record is guaranteed to be
useful for retrieval. The script then collects the distinct patient IDs referenced
by the sampled allergies and writes exactly those patient rows, topping up with a
small number of random filler patients so the patient demo reaches the target
size. Because every sampled allergy's `PATIENT` value is guaranteed to appear as a
patient `Id`, the join is never broken (0 orphaned allergy rows).

Allergy sampling is **balanced across allergy categories**. The full allergy
table is dominated by `environment` records (roughly 365k environment, 116k food,
49k medication), so a naive top-N or uniform-random sample skews almost entirely
to `environment` and leaves the `food` and `medication` demos empty. To avoid
this, the script uses stratified reservoir sampling with a per-category target so
all three categories are strongly represented. For a 7,000-row allergy demo the
split is approximately:

| Category | Rows |
| --- | ---: |
| `food` | 2,334 |
| `environment` | 2,333 |
| `medication` | 2,333 |

This balance is what makes category and severity demos meaningful. The sampled
food and medication rows carry real allergens (Shellfish, Peanut, Eggs, Fish,
Tree nut, Wheat, Soy, Cow's milk; Penicillin, Aspirin, Ibuprofen, Lisinopril,
cefdinir, Sulfamethoxazole) and populated reaction severities (roughly MODERATE
2,491, MILD 912, SEVERE 627, with the remainder unrecorded).

The demo dataset is deterministic because a fixed random seed is used. This
means the same command produces the same subset, making project results easier
to reproduce.

Default command:

```bash
cd LLM-App
./.venv/bin/python scripts/create_demo_dataset.py --allergy-rows 7000 --seed 42
```

Output:

```text
LLM-App/data/allergies_demo.csv
LLM-App/data/patients_demo.csv
```

To create a larger demo subset:

```bash
cd LLM-App
./.venv/bin/python scripts/create_demo_dataset.py --allergy-rows 10000 --seed 42
```

The chosen demo size of 7,000 allergy records is a practical compromise. It is
large enough to demonstrate filtering by allergy category, severity, gender,
age group, and location — with all three categories well populated — but small
enough to ingest quickly during development (roughly two to three minutes to
embed on a laptop CPU).

## 5. App Dataset Configuration

Dataset file paths are configured in:

```text
LLM-App/app/config.py
```

Default settings:

```text
PATIENTS_CSV=data/patients_demo.csv
ALLERGIES_CSV=data/allergies_demo.csv
```

To use the full dataset instead:

```bash
export PATIENTS_CSV=data/patients.csv
export ALLERGIES_CSV=data/allergies.csv
```

When the selected dataset files change, the backend detects stale Chroma
metadata and rebuilds the collection from the configured CSV files.

This avoids a common problem in RAG systems: the vector database may contain old
records even after the source CSV files have changed. The application stores the
dataset file names in Chroma metadata and uses that metadata to decide whether a
collection is current or stale.

## 6. Table Relationship

The common field is the patient identifier:

| Table | Join Field |
| --- | --- |
| `patients.csv` / `patients_demo.csv` | `Id` |
| `allergies.csv` / `allergies_demo.csv` | `PATIENT` |

Join rule:

```text
patients.Id = allergies.PATIENT
```

Each allergy row belongs to one patient. During ingestion, the app joins each
allergy row to its matching patient row.

The relationship is one-to-many:

```text
one patient -> many allergy records
```

For example, one patient may have allergies to shellfish, aspirin, animal
dander, or other substances. Each allergy appears as a separate row in the
allergy table. The RAG app indexes each allergy row separately so that retrieval
can return focused allergy records instead of very large patient profiles.

## 7. Patient Fields Used

The app uses these patient fields:

- `Id`
- `FIRST`
- `MIDDLE`
- `LAST`
- `BIRTHDATE`
- `GENDER`
- `RACE`
- `ETHNICITY`
- `CITY`
- `STATE`
- `COUNTY`

Derived patient fields:

- `patient_name`
- `patient_name_key`
- `first_name`
- `last_name`
- `age_group`

`patient_name_key` is the lower-case form of the full patient name. It is used
for exact name filtering from the chat UI.

The chat interface should allow users to ask questions using patient names
rather than internal patient UUIDs. The UUID remains available internally for
joins and debugging, but it is not user-friendly. For this reason, the ingestion
process creates both a display name and a normalized lowercase lookup key.

## 8. Allergy Fields Used

The app uses these allergy fields:

- `START`
- `STOP`
- `PATIENT`
- `ENCOUNTER`
- `CODE`
- `SYSTEM`
- `DESCRIPTION`
- `TYPE`
- `CATEGORY`
- `REACTION1`
- `DESCRIPTION1`
- `SEVERITY1`
- `REACTION2`
- `DESCRIPTION2`
- `SEVERITY2`

Derived allergy field:

- `severity`

`severity` stores the highest available reaction severity from `SEVERITY1` and
`SEVERITY2`.

Some allergy records have one reaction, some have two, and some have no reaction
details. The derived `severity` field helps retrieval and filtering because a
question such as "Which allergies have moderate reactions?" can be answered by
filtering or ranking records with `severity = MODERATE`.

## 9. Fields Intentionally Not Indexed

The app does not index PII-heavy fields such as:

- `SSN`
- `DRIVERS`
- `PASSPORT`
- full street `ADDRESS`
- `LAT`
- `LON`
- `INCOME`

These fields are excluded because the RAG demo is intended to answer clinical
allergy questions, not expose identity or financial information.

This exclusion is also important for the guardrail demonstration. The guardrail
system should prevent inappropriate disclosure, but the data pipeline should
also avoid placing unnecessary sensitive fields into the vector database. This
is a defense-in-depth design: sensitive fields are removed before retrieval, and
the guardrails still inspect input, retrieved context, and model output.

## 10. Indexed Document Shape

The app creates one Chroma document per allergy row.

The indexed document is a natural-language representation of the joined patient
and allergy record. Converting the structured CSV row into readable text helps
embedding models capture the clinical meaning of the record. At the same time,
structured metadata is stored separately so that exact filters can be applied
before or during retrieval.

Each document contains:

- patient name
- internal patient ID
- birthdate-derived age group
- gender
- race
- ethnicity
- city, county, state
- allergy description
- allergy category
- allergy type
- allergy code and coding system
- start and stop dates
- encounter ID
- reaction descriptions
- reaction severities

Conceptual document:

```text
Allergy Record:
Patient ID: <internal UUID>.
Patient name: <full patient name>.
Birthdate: <birthdate>.
Age group: <pediatric|adult|senior>.
Gender: <F|M>.
Race: <race>.
Ethnicity: <ethnicity>.
Location: <city>, <county>, <state>.
Allergy: <description>.
Category: <food|medication|environment>.
Type: allergy.
Code: <clinical code>.
Start date: <date>.
Stop date: <date or active>.
Encounter: <encounter id>.
Reactions: <reaction descriptions and severities>.
```

This format allows the model to answer questions such as:

- "Which allergies have moderate reactions?"
- "What reactions are recorded for shellfish allergies?"
- "Summarize this patient's allergy records."
- "Which food allergies are active?"
- "What allergy categories appear in the retrieved records?"

## 11. Indexed Metadata

The metadata stored with each Chroma document includes:

- `source`
- `document_type`
- `row_index`
- `patient_id`
- `patient_name`
- `patient_name_key`
- `first_name`
- `last_name`
- `encounter_id`
- `allergy_code`
- `allergy_system`
- `allergy_description`
- `allergy_type`
- `allergy_category`
- `allergy_start`
- `allergy_stop`
- `reaction1_code`
- `reaction1_description`
- `reaction1_severity`
- `reaction2_code`
- `reaction2_description`
- `reaction2_severity`
- `severity`
- `gender`
- `race`
- `ethnicity`
- `age_group`
- `city`
- `state`
- `county`
- `dataset_patients_file`
- `dataset_allergies_file`

For chat UI flows, prefer `patient_name` rather than `patient_id`.
`patient_id` remains useful internally for joins, debugging, and traceability.

Metadata is important because vector similarity alone is not always precise
enough for healthcare-style questions. For example, if the user asks about a
specific patient or a specific severity level, the application can apply exact
metadata filters before asking the language model to summarize the retrieved
context.

Example metadata filters:

```json
{"severity": "MODERATE"}
```

```json
{"allergy_category": "food"}
```

```json
{"patient_name": "Cole117 Colin861 Lind531"}
```

The API normalizes `patient_name` into `patient_name_key` so user-facing names
can be used in chat requests.

## 12. Ingestion Flow

Ingestion code:

```text
LLM-App/app/ingestion.py
```

Startup flow:

1. FastAPI starts from `app.main`.
2. The app opens the persisted Chroma collection.
3. The app checks whether existing Chroma metadata matches the configured CSV
   paths.
4. If the collection is empty or stale, the app rebuilds it.
5. The app reads the configured patients CSV and allergies CSV.
6. It joins rows using `patients.Id = allergies.PATIENT`.
7. It writes one Chroma document per allergy row.
8. It stores filterable metadata with each document.

Expected Chroma document count:

- Demo dataset: approximately `7000`
- Full dataset: approximately `529829`

The Chroma document count should match the number of allergy rows being
indexed, because each allergy row becomes one vector document. The patient table
is used to enrich allergy records, not to create separate patient-only documents
during the default joined allergy ingestion flow.

If `/health` reports a document count of `0`, ingestion did not complete. If it
reports approximately `529829`, the backend is using the full dataset. If it
reports approximately `7000`, the backend is using the resized demo dataset.

## 13. Example Chat Query

User-facing query by patient name:

```json
{
  "question": "Summarize Cole117 Colin861 Lind531's allergy records and reactions.",
  "session_id": "demo",
  "filters": {
    "patient_name": "Cole117 Colin861 Lind531"
  }
}
```

The API normalises `patient_name` to `patient_name_key` before querying Chroma.

General allergy query:

```json
{
  "question": "Which allergies have moderate reactions?",
  "session_id": "demo",
  "filters": {
    "severity": "MODERATE"
  }
}
```

These example queries are designed for the chat interface. Users should not need
to know internal patient IDs. They can ask a natural-language question, and the
application can use metadata filters when needed.

## 14. Verification Commands

Check backend health:

```bash
curl -s http://localhost:8000/health | jq
```

For the demo dataset, expect:

```text
doc_count: 7000
guardrails_active: true
```

Run a retrieval query:

```bash
curl -s http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Which allergies have moderate reactions?",
    "filters": {"severity": "MODERATE"},
    "top_k": 10
  }' | jq
```

If the query returns sources and an answer, the CSV files have been read,
joined, embedded, and stored in the vector database successfully. If no sources
are returned, check:

1. whether the backend startup completed;
2. whether the configured CSV files exist;
3. whether `/health` reports the expected document count;
4. whether the Chroma collection was rebuilt after changing dataset files;
5. whether the query filters are too restrictive.

## 15. Design Rationale

The dataset preparation was designed around four goals.

First, the data should be clinically meaningful. Allergy records with reaction
descriptions and severity levels provide a useful healthcare domain for RAG
questions.

Second, the data should be privacy-conscious. Although the dataset is synthetic,
the app still excludes PII-heavy columns such as SSN, address, coordinates, and
income. This mirrors good practice for real-world healthcare systems.

Third, retrieval should be efficient. The demo subset reduces startup time and
keeps local development practical.

Fourth, the chat interface should be user-friendly. The application supports
patient-name filtering rather than requiring users to enter UUID-style patient
IDs.

## 16. Guardrail Relevance

This dataset supports the guardrail demo in several ways:

- L1 input normalization can decode encoded prompts before classification.
- L2 classification can block prompt injection or data exfiltration attempts.
- L4 RAG sanitization can remove unsafe retrieved chunks before prompting.
- L5 output scanning can redact PII-like output while preserving clinical codes.
- L6 session tracking can rate-limit repeated requests.

The allergy dataset is useful because it contains realistic clinical terms,
codes, severities, and demographic fields. This allows the guardrail system to
be demonstrated on realistic healthcare-style queries without using real
patient data.

## 17. Citation

If this dataset is referenced in a report or presentation, cite:

- Hugging Face dataset:
  `richardyoung/synthea-575k-patients`
- Synthea paper:
  Walonoski, Jason, et al. "Synthea: An approach, method, and software
  mechanism for generating synthetic patients and the synthetic electronic
  health care record." Journal of the American Medical Informatics Association,
  2018.
