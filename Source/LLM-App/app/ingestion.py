"""Document ingestion — patient + allergy CSVs → ChromaDB.

The indexed unit is **one Chroma document per allergy event**, enriched with
demographic fields from the matching patient row (joined on the patient UUID:
``allergies.PATIENT == patients.Id``).

PII-heavy patient fields (SSN, driver's licence, passport, street address,
lat/lon, income) are intentionally **not** indexed — the guardrail demos focus
on clinical allergy facts, not raw identity data.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import chromadb

# Patient columns we keep (everything else, incl. PII, is dropped on load).
_PATIENT_FIELDS = (
    "FIRST", "MIDDLE", "LAST", "GENDER", "RACE", "ETHNICITY",
    "CITY", "COUNTY", "STATE", "BIRTHDATE",
)

_SEVERITY_RANK = {"MILD": 1, "MODERATE": 2, "SEVERE": 3}


def _load_patients(path: str | Path) -> dict[str, dict[str, str]]:
    """Map patient UUID -> the (non-PII) demographic fields we index."""
    patients: dict[str, dict[str, str]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row.get("Id", "")
            if pid:
                patients[pid] = {k: row.get(k, "") for k in _PATIENT_FIELDS}
    return patients


def _age_group(birthdate: str, ref: str) -> str:
    """Bucket age (at allergy onset, or today) into pediatric/adult/senior."""
    try:
        birth_year = int(birthdate[:4])
        ref_year = int(ref[:4]) if ref else date.today().year
    except (ValueError, TypeError):
        return ""
    age = ref_year - birth_year
    if age < 18:
        return "pediatric"
    if age < 65:
        return "adult"
    return "senior"


def _highest_severity(row: dict[str, str]) -> str:
    """Return the highest recorded severity across the two reaction slots."""
    sevs = [row.get("SEVERITY1", ""), row.get("SEVERITY2", "")]
    ranked = [s.upper() for s in sevs if s.upper() in _SEVERITY_RANK]
    return max(ranked, key=_SEVERITY_RANK.get, default="")


def _reactions_text(row: dict[str, str]) -> str:
    """Render the recorded reactions (description + severity) as text."""
    items: list[str] = []
    for desc_key, sev_key in (("DESCRIPTION1", "SEVERITY1"), ("DESCRIPTION2", "SEVERITY2")):
        desc = row.get(desc_key, "").strip()
        if desc:
            sev = row.get(sev_key, "").strip()
            items.append(f"{desc} [{sev}]" if sev else desc)
    return "; ".join(items) if items else "none recorded"


def _allergy_to_text(a: dict[str, str], p: dict[str, str], age_group: str) -> str:
    """Build the natural-language document for one allergy event."""
    name = " ".join(v for v in (p.get("FIRST", ""), p.get("MIDDLE", ""), p.get("LAST", "")) if v)
    onset = a.get("START", "") or "unknown"
    resolved = f", resolved {a['STOP']}" if a.get("STOP") else ""
    severity = _highest_severity(a) or "not recorded"
    return (
        f"Allergy Record for patient {name} "
        f"({p.get('GENDER', '')}, {age_group or 'unknown age'}, "
        f"{p.get('RACE', '')} {p.get('ETHNICITY', '')}) "
        f"in {p.get('CITY', '')}, {p.get('COUNTY', '')}, {p.get('STATE', '')}. "
        f"Allergen: {a.get('DESCRIPTION', '')} "
        f"(category: {a.get('CATEGORY', '')}, type: {a.get('TYPE', 'allergy')}). "
        f"Onset: {onset}{resolved}. Severity: {severity}. "
        f"Reactions: {_reactions_text(a)}. "
        f"Clinical code: {a.get('CODE', '')} ({a.get('SYSTEM', '')})."
    )


def ingest_allergies(
    patients_path: str | Path,
    allergies_path: str | Path,
    collection: chromadb.Collection,
    batch_size: int = 1000,
) -> int:
    """Index one document per allergy event, enriched with patient demographics.

    Returns the number of documents in the collection after ingestion.
    """
    patients = _load_patients(patients_path)

    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    def _flush() -> None:
        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            documents.clear()
            metadatas.clear()
            ids.clear()

    with open(allergies_path, newline="", encoding="utf-8") as f:
        for i, a in enumerate(csv.DictReader(f)):
            pid = a.get("PATIENT", "")
            p = patients.get(pid, {})
            age_group = _age_group(p.get("BIRTHDATE", ""), a.get("START", ""))
            first, last = p.get("FIRST", ""), p.get("LAST", "")
            patient_name = " ".join(
                v for v in (first, p.get("MIDDLE", ""), last) if v
            )

            documents.append(_allergy_to_text(a, p, age_group))
            metadatas.append(
                {
                    "source": "allergies",
                    "patient_id": pid,
                    "patient_name": patient_name,
                    "first_name": first,
                    "last_name": last,
                    "allergy_description": a.get("DESCRIPTION", ""),
                    "allergy_category": a.get("CATEGORY", ""),
                    "allergy_type": a.get("TYPE", ""),
                    "allergy_code": a.get("CODE", ""),
                    "encounter_id": a.get("ENCOUNTER", ""),
                    "severity": _highest_severity(a),
                    "gender": p.get("GENDER", ""),
                    "race": p.get("RACE", ""),
                    "ethnicity": p.get("ETHNICITY", ""),
                    "age_group": age_group,
                    "city": p.get("CITY", ""),
                    "county": p.get("COUNTY", ""),
                    "state": p.get("STATE", ""),
                }
            )
            ids.append(f"allergy_{i}")

            if len(documents) >= batch_size:
                _flush()

    _flush()
    return collection.count()


def resolve_data_paths(data_dir: str | Path = "data") -> tuple[Path, Path]:
    """Prefer the full patients.csv/allergies.csv; fall back to the *_demo.csv."""
    data_dir = Path(data_dir)
    patients = data_dir / "patients.csv"
    allergies = data_dir / "allergies.csv"
    if not patients.exists():
        patients = data_dir / "patients_demo.csv"
    if not allergies.exists():
        allergies = data_dir / "allergies_demo.csv"
    return patients, allergies


def ingest_csv(
    csv_path: str | Path,
    collection: chromadb.Collection,
    batch_size: int = 1000,
) -> int:
    """Ingest an uploaded allergies CSV, joined to the on-disk patients file.

    Kept for the /ingest upload endpoint. The uploaded file is treated as an
    allergies export; patient demographics come from the resolved patients file.
    """
    patients_path, _ = resolve_data_paths()
    return ingest_allergies(patients_path, csv_path, collection, batch_size)
