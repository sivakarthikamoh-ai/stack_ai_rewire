---
name: ai-native-model-serving
description: >
  Bare-minimum skill for Stack AI Rewire - MLE Assignment 1. Trains the model artifact and writes the
  serving spec, then pauses — it deliberately does NOT generate the FastAPI wrapper,
  Dockerfile, CI/CD pipeline, tests, or self-review. Those are built by the learner working
  directly with Claude, and the learner's own deliverable includes
   extending this file with the steps they used to do it.
---

# AI-Native Model Serving — Assignment Runner (Step 0-4)

You are Claude, running **Stack AI Rewire - MLE — Assignment 1: AI-Native Model Serving**
in Claude Code against the learner's repo. This skill covers producing the model artifact,
writing the serving spec, building the FastAPI service and Docker/CI-CD wrapper, adding the
validation test suite, and doing the final self-review handoff. The learner is expected to
follow the exact checks and file layout below and only stop when the service, tests, and
pipeline are green.

## Required input
- `data/house_prices.csv` — provided, the training data. Do not edit it.
- `train_model.py` — provided. You run this yourself in Step 0.
- `requirements.txt` — provided, pins the training dependencies (pandas, scikit-learn, joblib).

## Repo scaffold this skill produces
```
.
├── data/house_prices.csv        <- provided, do not edit
├── train_model.py               <- provided
├── requirements.txt              <- provided
├── model.joblib                  <- produced by you in Step 0
├── model_card.md                 <- produced by you in Step 0
└── spec.md                       <- produced by you in Step 1
```
Everything else (app/, Dockerfile, .gitlab-ci.yml, tests/, and any notes/logs the learner
decides to keep) gets created afterward, by hand, outside this skill.

---

## Step 0 — Produce the model artifact
Before anything else, make sure `model.joblib` and `model_card.md` exist. If they don't:
1. Set up a Python environment if one isn't already active (e.g. `python3 -m venv .venv &&
   source .venv/bin/activate`), then `pip install -r requirements.txt`.
2. Run `python3 train_model.py`. It reads `data/house_prices.csv` and writes `model.joblib`
   and `model_card.md` into the repo root — don't write either of these files yourself, and
   don't modify `train_model.py` or the dataset to hit a particular result.
3. Confirm both files were produced (check the script's own train/test R² output for a sanity
   check — it should print without erroring) before moving on.

If `model.joblib` and `model_card.md` already exist (e.g. a previous run), don't retrain —
just confirm they're consistent with `train_model.py`'s current contents and move on.

## Step 1 — Write the spec, against a fixed productionization checklist
Read `model_card.md`. Write `spec.md`, covering every item below — do not skip one silently;
if an item genuinely doesn't apply, say why in the spec rather than omitting it.

**API contract**
- Endpoints: `/predict` (per the model card's input schema) and `/health`.
- Request/response schema: field names, types, required/optional, matching `model_card.md`
  exactly (do not loosen types the model card says are strict).
- Explicit error responses for: malformed JSON, missing required field, wrong type,
  out-of-range value, empty payload — each with a specific HTTP status code and a consistent
  error body shape (e.g. `{"error": "...", "field": "...", "detail": "..."}`), not a bare 500.

**Non-functional requirements** (pick at least three, don't leave this section thin)
- Versioning: how the model/API version is surfaced (e.g. in `/health`'s response), and how
  image tags map to commits.
- Observability: what gets logged per request (request id, latency, input shape, status code)
  and at what level.
- Resource limits: max request payload size; a request timeout.
- Config: what's environment-driven (model path, log level, port) vs. hardcoded — nothing
  environment-specific should be hardcoded.
- Startup behavior: what happens if `model.joblib` fails to load (the service should fail
  fast and loud, not serve traffic with no model).

**Security baseline** (address all of these in the spec, even briefly)
- No secrets or credentials in code or image layers.
- Restrictive CORS (don't default to `*` without saying so is a deliberate choice).
- Dependency pinning strategy.
- Docker: run as a non-root user, minimal final-stage image.

**Then stop.** Tell the learner `spec.md` is ready for review and wait for them to either say
to proceed or ask for changes. This is the one pause in this skill. Once they confirm the
spec, this skill has nothing further to do — building the service, container, and pipeline
happens in a normal session from here, guided by `spec.md`. Their runbook covers that part.

---

## Step 2 — Build the wrapper, Dockerfile, and CI/CD
Build the production-shaped serving layer around the trained model artifact. Create the files
below in the repo root and keep the implementation aligned to `spec.md` and `model_card.md`.

1. Create `app/__init__.py`, `app/schema.py`, and `app/main.py`.
2. In `app/schema.py`, define `PredictionRequest` using Pydantic `StrictFloat` and `StrictInt`
   fields for `sqft`, `bedrooms`, `bathrooms`, `age_years`, and `location_score`, matching the
   ranges from `model_card.md` (`sqft` 300-8000, `bedrooms` 0-10, `bathrooms` 0.5-8,
   `age_years` 0-150, `location_score` 0-10). Add `extra="forbid"` and keep the feature order
   exactly `sqft, bedrooms, bathrooms, age_years, location_score`.
3. In `app/main.py`, create a FastAPI app with:
   - `GET /health` returning `status`, `model_version`, `api_version`, `commit_sha`, and
     `timestamp`.
   - `POST /predict` accepting JSON, validating payloads against `PredictionRequest`,
     converting the validated payload to a single-row `pandas.DataFrame` with the exact column
     order above, and returning `{"predicted_price": ..., "currency": "USD", "model_version": ...}`.
   - fail-fast startup logic that attempts to load `model.joblib` from `MODEL_PATH` and exits if it
     cannot be loaded.
   - request logging including request ID, HTTP method/path, latency, status code, and relevant
     error codes; include `X-Request-ID` in response headers.
   - CORS limited to explicit origins from `CORS_ALLOWED_ORIGINS` and no wildcard origin.
   - JSON responses for malformed JSON, empty payload, missing required field, invalid type,
     out-of-range value, and oversized payload.
4. Ensure the model is loaded lazily or on startup in a way that works with FastAPI test client
   usage and direct runtime use. Do not silently coerce strings to numbers in the API boundary.
5. Create a multi-stage `Dockerfile` with a lean final stage based on `python:3.13-slim`, install
   runtime dependencies from `requirements.txt`, copy `app/` and `model.joblib`, and run the app as a
   non-root `appuser` (UID/GID 1000). Expose port 8080 and run `uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers ${WORKERS}`.
6. Create `.dockerignore` to exclude `.git`, `.venv`, `__pycache__`, `.pytest_cache`, test files,
   and other local/editor artifacts while keeping `model.joblib` in the image.
7. Create `.gitlab-ci.yml` with stages: `lint`, `unit`, `contract`, `integration`, `build`, `push`,
   `qa`. Use `python:3.13-slim` for lint and test jobs, `docker:24.1` for build/push and QA smoke
   tests, install from `requirements.txt`, run `ruff check app tests`, and execute:
   - `pytest tests/test_unit.py -q`
   - `pytest tests/test_contract.py -q`
   - `pytest tests/test_integration.py -q`
8. In the push stage, log in to Docker Hub using `$DOCKERHUB_USERNAME` and `$DOCKERHUB_TOKEN`,
   tag the built image with `${CI_COMMIT_SHORT_SHA}`, and push it to a registry path such as
   `$DOCKERHUB_USERNAME/house-price-api:${CI_COMMIT_SHORT_SHA}`.
9. Add a QA stage with `environment: name: qa` that runs only for `main` or `qa`, pulls the pushed
   image, starts it locally on port 8080, calls `/health`, then calls `/predict` with a valid sample
   payload, and removes the container when the smoke test passes.
10. Check the repo root for the finished files and confirm their contents match the contract before
    moving on: `app/main.py`, `app/schema.py`, `Dockerfile`, `.dockerignore`, `.gitlab-ci.yml`.

## Step 3 — Add the tests
Create the automated test suite under `tests/` with explicit edge cases, not just happy paths.

1. Create `tests/test_unit.py` to validate the model request schema directly.
   - Confirm that a valid payload passes.
   - Confirm `sqft=250` raises validation.
   - Confirm a string value such as `"1500"` for `sqft` raises validation.
2. Create `tests/test_contract.py` to validate the API contract.
   - `GET /health` returns 200 and includes `status`, `model_version`, `api_version`, and
     `timestamp`.
   - `POST /predict` with a valid payload returns 200 and a JSON object with keys
     `predicted_price`, `currency`, and `model_version`.
   - `POST /predict` with a missing required field returns 422 and the error payload includes
     `error: "missing_required_field"` and the offending field name.
   - `POST /predict` with an out-of-range value returns 422 and `error: "out_of_range"`.
3. Create `tests/test_integration.py` to validate end-to-end request handling.
   - Malformed JSON returns 400 and `error: "malformed_json"`.
   - Empty payload returns 400 and `error: "empty_payload"`.
   - Wrong type returns 422 and `error: "invalid_type"`.
4. After writing the tests, check the suite with:
   - `pytest tests/test_unit.py -q`
   - `pytest tests/test_contract.py -q`
   - `pytest tests/test_integration.py -q`
5. Do the mutation check the assignment explicitly calls for: temporarily weaken one validation
   rule in `app/schema.py`, run the relevant tests, confirm they fail, and then restore the strict
   validation before final submission. Record the result in your review notes so you can defend the
   test suite as real, not assumed.

## Step 4 — Self-review, cleanup, and handoff
Do a final review pass before the merge request is opened.

1. Run the full test suite:
   - `pytest -q`
2. Review the code diff and the local repo state with `git diff --stat` and `git status --short`.
   Look for security and quality issues: secrets in code, hardcoded environment values,
   unrestricted CORS, missing validation, weak Docker defaults, or any accidental inclusion of
   local credentials or caches.
3. If the reviewer or your own audit finds a problem, fix it or explicitly note why it is out of
   scope. Do not leave obvious security or validation issues unresolved.
4. Ensure `spec.md` still matches the built service. If the implementation differs from the spec,
   update either the code or the spec so the final submission is consistent.
5. Confirm the QA stage in `.gitlab-ci.yml` is a real smoke test that pulls the image and calls the
   live endpoints against the built container, not just a placeholder job.
6. Final handoff: summarize the completed artifact list, the validation commands you ran, the
   mutation-check result, and the decisions you made in `spec.md` before opening the merge request.
   At this point, stop and ask for review or proceed to `git checkout -b assignment-1-model-serving`
   and submit the MR with the GitLab pipeline evidence.

---

## The deliverable after Step 4
Once the learner has completed the service, container, CI/CD pipeline, tests, and self-review,
this updated file is the reusable instruction set that should be handed off to a fresh Claude
session to reproduce the same work on a different model and dataset. Keep the steps concrete,
imperative, and based on the exact files above. Do not leave any of the required work implicit
or vague.
