from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt

FEATURES = ["sqft", "bedrooms", "bathrooms", "age_years", "location_score"]


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sqft: StrictFloat = Field(..., ge=300.0, le=8000.0)
    bedrooms: StrictInt = Field(..., ge=0, le=10)
    bathrooms: StrictFloat = Field(..., ge=0.5, le=8.0)
    age_years: StrictInt = Field(..., ge=0, le=150)
    location_score: StrictFloat = Field(..., ge=0.0, le=10.0)
