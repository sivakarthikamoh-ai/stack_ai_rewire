from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["model_version"] == "1.0.0"
    assert body["api_version"] == "1.0.0"
    assert "timestamp" in body


def test_predict_success():
    response = client.post(
        "/predict",
        json={
            "sqft": 1500,
            "bedrooms": 3,
            "bathrooms": 2.0,
            "age_years": 10,
            "location_score": 7.5,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body.keys()) == {"predicted_price", "currency", "model_version"}
    assert body["currency"] == "USD"
    assert body["model_version"] == "1.0.0"
    assert isinstance(body["predicted_price"], (int, float))


def test_missing_required_field_returns_422():
    response = client.post(
        "/predict",
        json={
            "sqft": 1500,
            "bedrooms": 3,
            "bathrooms": 2.0,
            "age_years": 10,
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "missing_required_field"
    assert body["field"] == "location_score"


def test_out_of_range_value_returns_422():
    response = client.post(
        "/predict",
        json={
            "sqft": 250,
            "bedrooms": 3,
            "bathrooms": 2.0,
            "age_years": 10,
            "location_score": 7.5,
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "out_of_range"
    assert body["field"] == "sqft"
