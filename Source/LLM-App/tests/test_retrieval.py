"""Tests for CSV ingestion and ChromaDB retrieval."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from app.ingestion import ingest_csv
from app.retriever import retrieve


def _write_sample_csv(path: Path, n_rows: int = 10) -> None:
    """Write a small healthcare CSV for testing."""
    headers = [
        "Name", "Age", "Gender", "Blood Type", "Medical Condition",
        "Date of Admission", "Doctor", "Hospital", "Insurance Provider",
        "Billing Amount", "Room Number", "Admission Type", "Discharge Date",
        "Medication", "Test Results", "Length of Stay",
    ]
    conditions = ["Infections", "Flu", "Cancer", "Asthma", "Heart Disease"]
    doctors = ["Dr. Alpha", "Dr. Beta", "Dr. Gamma", "Dr. Alpha", "Dr. Beta"]
    medications = ["Azithromycin", "Tamiflu", "Cisplatin", "Prednisone", "Beta-blockers"]
    admission_types = ["Emergency", "Routine", "Elective", "Urgent", "Emergency"]
    test_results = ["Normal", "Abnormal", "Inconclusive", "Normal", "Abnormal"]
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for i in range(n_rows):
            writer.writerow([
                f"Patient_{i}", str(20 + i), "Male", "O+",
                conditions[i % len(conditions)],
                "2024-01-01", doctors[i % len(doctors)],
                "Test Hospital", "TestInsurance",
                "1000.00", str(100 + i), admission_types[i % len(admission_types)],
                "2024-01-05",
                medications[i % len(medications)],
                test_results[i % len(test_results)], "5",
            ])


def test_csv_ingestion_count(temp_chroma):
    """Ingestion should produce exactly N documents for N CSV rows."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test.csv"
        _write_sample_csv(csv_path, n_rows=10)
        count = ingest_csv(csv_path, temp_chroma)
    assert count == 10


def test_csv_ingestion_metadata_fields(temp_chroma):
    """Ingested docs should have all 8 metadata fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test.csv"
        _write_sample_csv(csv_path, n_rows=3)
        ingest_csv(csv_path, temp_chroma)

    results = temp_chroma.get(ids=["row_0"])
    meta = results["metadatas"][0]
    expected_keys = {"source", "row_index", "condition", "hospital",
                     "doctor", "medication", "admission_type",
                     "test_results", "blood_type", "age_group"}
    assert expected_keys.issubset(set(meta.keys()))
    assert meta["doctor"] == "Dr. Alpha"
    assert meta["medication"] == "Azithromycin"
    assert meta["age_group"] == "adult"


def test_retrieval_returns_results(temp_chroma):
    """Querying for a known condition should return relevant results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test.csv"
        _write_sample_csv(csv_path, n_rows=20)
        ingest_csv(csv_path, temp_chroma)

    results = retrieve("infections", temp_chroma, top_k=3)
    assert len(results) == 3
    # Verify each result has content
    for r in results:
        assert len(r["content"]) > 0
        assert "Patient Record" in r["content"]


def test_retrieval_top_k(temp_chroma):
    """top_k parameter should limit the number of results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test.csv"
        _write_sample_csv(csv_path, n_rows=20)
        ingest_csv(csv_path, temp_chroma)

    results_2 = retrieve("patient", temp_chroma, top_k=2)
    results_5 = retrieve("patient", temp_chroma, top_k=5)
    assert len(results_2) == 2
    assert len(results_5) == 5


def test_retrieval_with_doctor_filter(temp_chroma):
    """Filtering by doctor should return only that doctor's patients."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test.csv"
        _write_sample_csv(csv_path, n_rows=20)
        ingest_csv(csv_path, temp_chroma)

    results = retrieve(
        "patient treatment", temp_chroma, top_k=10,
        filters={"doctor": "Dr. Alpha"},
    )
    assert len(results) > 0
    for r in results:
        assert r["metadata"]["doctor"] == "Dr. Alpha"


def test_retrieval_with_condition_filter(temp_chroma):
    """Filtering by condition should return only matching records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test.csv"
        _write_sample_csv(csv_path, n_rows=20)
        ingest_csv(csv_path, temp_chroma)

    results = retrieve(
        "treatment", temp_chroma, top_k=10,
        filters={"condition": "Flu"},
    )
    assert len(results) > 0
    for r in results:
        assert r["metadata"]["condition"] == "Flu"
