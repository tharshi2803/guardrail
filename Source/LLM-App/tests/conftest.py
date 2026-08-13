"""Shared test fixtures for the RAG QA app."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import chromadb
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def temp_chroma():
    """Ephemeral in-memory ChromaDB collection for tests."""
    client = chromadb.Client()  # in-memory
    collection = client.get_or_create_collection("test_healthcare")
    yield collection
    client.delete_collection("test_healthcare")


@pytest.fixture()
def mock_anthropic_response():
    """Return a factory that patches anthropic to return a canned answer."""

    def _make(answer_text: str = "This is a test answer from the LLM."):
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=answer_text)]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg
        return mock_client

    return _make


@pytest.fixture()
def test_client(mock_anthropic_response):
    """FastAPI TestClient with mocked LLM and in-memory ChromaDB."""
    # Patch ChromaDB to use in-memory client
    in_memory_client = chromadb.Client()
    collection = in_memory_client.get_or_create_collection("test_healthcare")

    # Add a few sample documents
    collection.add(
        documents=[
            "Patient Record: Name: John Doe, Age: 45, Gender: Male, Blood Type: O+, Medical Condition: Infections, Date of Admission: 2024-01-15, Doctor: Dr. Smith, Hospital: Northwestern Memorial Hospital, Insurance Provider: Blue Cross, Billing Amount: $5000.00, Room Number: 201, Admission Type: Emergency, Discharge Date: 2024-01-22, Medication: Azithromycin, Test Results: Abnormal, Length of Stay: 7 days",
            "Patient Record: Name: Jane Smith, Age: 30, Gender: Female, Blood Type: A-, Medical Condition: Flu, Date of Admission: 2024-02-10, Doctor: Dr. Johnson, Hospital: UI Health, Insurance Provider: Aetna, Billing Amount: $1500.00, Room Number: 105, Admission Type: Routine, Discharge Date: 2024-02-12, Medication: Tamiflu, Test Results: Normal, Length of Stay: 2 days",
            "Patient Record: Name: Bob Wilson, Age: 65, Gender: Male, Blood Type: B+, Medical Condition: Heart Disease, Date of Admission: 2024-03-01, Doctor: Dr. Lee, Hospital: UChicago Medicine, Insurance Provider: Medicare, Billing Amount: $25000.00, Room Number: 410, Admission Type: Emergency, Discharge Date: 2024-03-15, Medication: Lisinopril, Test Results: Abnormal, Length of Stay: 14 days",
        ],
        metadatas=[
            {"source": "healthcare_dataset", "row_index": 0, "condition": "Infections", "hospital": "Northwestern Memorial Hospital", "doctor": "Dr. Smith", "medication": "Azithromycin", "admission_type": "Emergency", "test_results": "Abnormal", "blood_type": "O+", "age_group": "adult"},
            {"source": "healthcare_dataset", "row_index": 1, "condition": "Flu", "hospital": "UI Health", "doctor": "Dr. Johnson", "medication": "Tamiflu", "admission_type": "Routine", "test_results": "Normal", "blood_type": "A-", "age_group": "adult"},
            {"source": "healthcare_dataset", "row_index": 2, "condition": "Heart Disease", "hospital": "UChicago Medicine", "doctor": "Dr. Lee", "medication": "Lisinopril", "admission_type": "Emergency", "test_results": "Abnormal", "blood_type": "B+", "age_group": "senior"},
        ],
        ids=["row_0", "row_1", "row_2"],
    )

    # Patch the module-level state in main
    import app.main as main_mod

    main_mod._collection = collection
    main_mod._chroma_client = in_memory_client

    mock_client = mock_anthropic_response()

    with patch("app.llm_client.get_client", return_value=mock_client):
        with patch("app.rules_loader.start_watcher"):
            with patch("app.rules_loader.stop_watcher"):
                # Use the app directly without lifespan (we set up state manually)
                from app.main import app

                yield TestClient(app, raise_server_exceptions=False)

    # Cleanup
    main_mod._collection = None
    main_mod._chroma_client = None
