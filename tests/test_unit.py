import pytest
from pydantic import ValidationError

from app.schema import PredictionRequest


def test_prediction_request_validates_expected_schema():
    payload = {
        "sqft": 1500.0,
        "bedrooms": 3,
        "bathrooms": 2.0,
        "age_years": 10,
        "location_score": 7.5,
    }

    request = PredictionRequest(**payload)
    assert request.model_dump() == payload


def test_prediction_request_rejects_out_of_range():
    with pytest.raises(ValidationError):
        PredictionRequest(
            sqft=250,
            bedrooms=3,
            bathrooms=2.0,
            age_years=10,
            location_score=7.5,
        )


def test_prediction_request_rejects_wrong_type():
    with pytest.raises(ValidationError):
        PredictionRequest(
            sqft="1500",
            bedrooms=3,
            bathrooms=2.0,
            age_years=10,
            location_score=7.5,
        )
