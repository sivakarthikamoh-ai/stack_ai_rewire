from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_malformed_json_is_rejected_cleanly():
    response = client.post(
        "/predict",
        data="{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "malformed_json"
    assert body["field"] is None


def test_empty_payload_is_rejected_cleanly():
    response = client.post(
        "/predict",
        data="",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "empty_payload"
    assert body["field"] is None


def test_invalid_type_is_rejected_cleanly():
    response = client.post(
        "/predict",
        json={
            "sqft": "1500",
            "bedrooms": 3,
            "bathrooms": 2.0,
            "age_years": 10,
            "location_score": 7.5,
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "invalid_type"
    assert body["field"] == "sqft"
