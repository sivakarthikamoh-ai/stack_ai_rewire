"""
Learner setup script. Run this ONCE, before starting the skill, to produce the model
artifact + model card the assignment builds a serving layer around.

Usage (from inside your activated venv):
    python3 train_model.py

Reads:
    data/house_prices.csv  -- provided, do not edit

Produces:
    model.joblib     -- the trained model artifact
    model_card.md     -- feature schema + example payload, read by the skill in Step 1
"""

import json
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

RANDOM_STATE = 42
DATA_PATH = "data/house_prices.csv"
FEATURES = ["sqft", "bedrooms", "bathrooms", "age_years", "location_score"]

FEATURE_SCHEMA = {
    "sqft": {"type": "float", "min": 300, "max": 8000, "description": "Living area in square feet"},
    "bedrooms": {"type": "int", "min": 0, "max": 10, "description": "Number of bedrooms"},
    "bathrooms": {"type": "float", "min": 0.5, "max": 8, "description": "Number of bathrooms (0.5 increments allowed)"},
    "age_years": {"type": "int", "min": 0, "max": 150, "description": "Age of the property in years"},
    "location_score": {"type": "float", "min": 0.0, "max": 10.0, "description": "Composite location desirability score, 0 (worst) to 10 (best)"},
}


def main():
    df = pd.read_csv(DATA_PATH)
    X = df[FEATURES]
    y = df["price"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )

    model = RandomForestRegressor(
        n_estimators=200, max_depth=12, random_state=RANDOM_STATE, n_jobs=-1
    )
    model.fit(X_train, y_train)

    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    print(f"Train R^2: {train_score:.4f}")
    print(f"Test  R^2: {test_score:.4f}")

    joblib.dump(model, "model.joblib")
    print("Saved model.joblib")

    example_input = X_test.iloc[0].to_dict()
    example_prediction = float(model.predict(X_test.iloc[[0]])[0])

    write_model_card(example_input, example_prediction, test_score)
    print("Saved model_card.md")


def write_model_card(example_input, example_prediction, test_score):
    schema_json = json.dumps(FEATURE_SCHEMA, indent=2)
    example_json = json.dumps(
        {k: (round(v, 2) if isinstance(v, float) else v) for k, v in example_input.items()},
        indent=2,
    )

    content = f"""# Model Card — House Price Predictor

## What this model does
Predicts a house sale price (USD, float) from five structural/location features. Trained on
a synthetic dataset (`data/house_prices.csv`) for training-program use — do not use for real
valuation.

## Artifact
`model.joblib` — a scikit-learn `RandomForestRegressor`, loadable with:
```python
import joblib
model = joblib.load("model.joblib")
```
Held-out test R^2: {test_score:.3f}

## Input schema (this is what your spec's request body should be built from)
```json
{schema_json}
```
All five fields are required. Call `model.predict(df)` with a single-row `pandas.DataFrame`
whose columns are named and ordered exactly `sqft, bedrooms, bathrooms, age_years,
location_score` — the model was fit on named columns and will warn (and may silently
mis-map values) if you pass a raw list/array instead. This is a real gap to account for in
your wrapper, not a hypothetical one.

## Output
A single float: predicted price in USD. No confidence interval or additional metadata is
produced by the model itself — if your spec wants one, that's something your serving layer
adds, not the model.

## Example input/output
Input:
```json
{example_json}
```
Predicted price: {example_prediction:,.2f}

## Things the model does NOT validate for you
- It will not reject out-of-range values (e.g. negative sqft, 400 bedrooms) — it will just
  produce a nonsense prediction. Input validation is the serving layer's job, not the model's.
- It will not reject wrong types gracefully — passing a string where a float is expected will
  raise inside `predict`, not return a clean error. This is deliberate: it's exactly the gap
  your spec's error-handling section needs to cover.
"""
    with open("model_card.md", "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    main()
