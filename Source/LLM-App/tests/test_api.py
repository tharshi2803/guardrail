"""Tests for FastAPI endpoints."""

from __future__ import annotations

from unittest.mock import patch


def test_health_endpoint(test_client):
    """GET /health should return status and collection info."""
    resp = test_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "doc_count" in data
    assert data["doc_count"] > 0


def test_query_endpoint(test_client):
    """POST /query with a valid question should return an answer."""
    resp = test_client.post("/query", json={"question": "What medications are used for infections?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert len(data["sources"]) > 0
    assert data["guard_result"]["passed"] is True


def test_rules_endpoint(test_client):
    """GET /rules should return the current guardrail config."""
    with patch("app.main.get_rules", return_value={"guardrails": {"input": {}}}):
        resp = test_client.get("/rules", auth=("guardrailuser", "tharshika123$$"))
    assert resp.status_code == 200
    data = resp.json()
    assert "guardrails" in data


def test_query_missing_question(test_client):
    """POST /query without a question field should return 422."""
    resp = test_client.post("/query", json={})
    assert resp.status_code == 422


def test_query_with_filters(test_client):
    """POST /query with filters should scope retrieval to matching records."""
    resp = test_client.post(
        "/query",
        json={
            "question": "What treatment was given?",
            "filters": {"doctor": "Dr. Smith"},
        },
    )
    # Should succeed (Dr. Smith exists in the test fixtures)
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert len(data["sources"]) > 0
