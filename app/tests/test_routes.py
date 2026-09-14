"""Integration tests for API endpoints. Uses mock LLM and stub DB."""
from unittest.mock import patch


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "Welcome" in body["message"]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_request_id_header(client):
    r = client.get("/health")
    assert "X-Request-ID" in r.headers
    assert "X-Response-Time-ms" in r.headers


def test_ready_reports_checks(client):
    r = client.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert "checks" in body
    assert "mongodb" in body["checks"]
    assert "redis" in body["checks"]


def test_recommendations_endpoint(client, sample_products):
    with patch("app.utils.db.db.get_products", return_value=sample_products), \
         patch("app.utils.db.db.get_products_by_ids",
               side_effect=lambda ids: [p for p in sample_products if p["id"] in ids]):
        r = client.get("/api/recommendations?query=sneakers&top_k=3")
        assert r.status_code == 200
        body = r.json()
        assert "recommendations" in body
        assert isinstance(body["recommendations"], list)


def test_recommendations_empty_query(client):
    r = client.get("/api/recommendations?query=")
    # Empty query is allowed by validation, may return empty list
    assert r.status_code in (200, 422)


def test_chat_single_message(client):
    r = client.post("/api/conversation", json={"message": "hello"})
    assert r.status_code == 200
    assert "reply" in r.json()


def test_chat_batch_messages(client):
    r = client.post(
        "/api/conversation", json={"message": ["hi", "hello"]}
    )
    assert r.status_code == 200
    assert "replies" in r.json()
    assert len(r.json()["replies"]) == 2


def test_chat_invalid_body(client):
    r = client.post("/api/conversation", json={"wrong": "field"})
    assert r.status_code == 422