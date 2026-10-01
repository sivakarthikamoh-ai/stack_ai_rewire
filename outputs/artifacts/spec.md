# House Price Predictor — API Serving Specification

## Overview
FastAPI service wrapping `model.joblib` (scikit-learn RandomForestRegressor) for real-time house price predictions. Service accepts structured property features and returns predicted sale price in USD.

---

## API Contract

### Endpoints

#### `POST /predict`
**Purpose:** Predict house price from structural/location features.

**Request Body:**
```json
{
  "sqft": {
    "type": "float",
    "required": true,
    "min": 300,
    "max": 8000,
    "description": "Living area in square feet"
  },
  "bedrooms": {
    "type": "integer",
    "required": true,
    "min": 0,
    "max": 10,
    "description": "Number of bedrooms"
  },
  "bathrooms": {
    "type": "float",
    "required": true,
    "min": 0.5,
    "max": 8,
    "description": "Number of bathrooms (0.5 increments allowed)"
  },
  "age_years": {
    "type": "integer",
    "required": true,
    "min": 0,
    "max": 150,
    "description": "Age of the property in years"
  },
  "location_score": {
    "type": "float",
    "required": true,
    "min": 0.0,
    "max": 10.0,
    "description": "Composite location desirability score, 0 (worst) to 10 (best)"
  }
}
```

**Response (Success: 200 OK):**
```json
{
  "predicted_price": 740653.64,
  "currency": "USD",
  "model_version": "1.0.0"
}
```

**Response (Error) — Malformed JSON (400):**
```json
{
  "error": "malformed_json",
  "field": null,
  "detail": "Request body is not valid JSON"
}
```

**Response (Error) — Missing Required Field (422):**
```json
{
  "error": "missing_required_field",
  "field": "sqft",
  "detail": "Field 'sqft' is required"
}
```

**Response (Error) — Wrong Type (422):**
```json
{
  "error": "invalid_type",
  "field": "sqft",
  "detail": "Field 'sqft' must be a float, got string"
}
```

**Response (Error) — Out-of-Range Value (422):**
```json
{
  "error": "out_of_range",
  "field": "sqft",
  "detail": "Field 'sqft' must be between 300 and 8000, got 250"
}
```

**Response (Error) — Empty Payload (400):**
```json
{
  "error": "empty_payload",
  "field": null,
  "detail": "Request body cannot be empty"
}
```

**Response (Error) — Payload Too Large (413):**
```json
{
  "error": "payload_too_large",
  "field": null,
  "detail": "Request body exceeds maximum size of 1MB"
}
```

**Response (Error) — Request Timeout (504):**
```json
{
  "error": "request_timeout",
  "field": null,
  "detail": "Request processing exceeded 30 seconds"
}
```

#### `GET /health`
**Purpose:** Service health check and version reporting.

**Response (Success: 200 OK):**
```json
{
  "status": "healthy",
  "model_version": "1.0.0",
  "api_version": "1.0.0",
  "commit_sha": "abc123def456",
  "timestamp": "2025-01-15T10:30:45Z"
}
```

**Response (Error: 503 Service Unavailable)** — if model fails to load at startup:
```json
{
  "status": "unhealthy",
  "detail": "Model artifact failed to load: model.joblib not found or corrupted"
}
```

---

## Non-Functional Requirements

### 1. Versioning
- **Model Version:** Sourced from `MODEL_VERSION` environment variable (default: `"1.0.0"`). Returned in `/health` and `/predict` responses.
- **API Version:** Hardcoded as `"1.0.0"` in the service, returned in `/health`.
- **Commit SHA:** Docker image tag format is `model-serving:v1.0.0-<SHORT_GIT_SHA>` (e.g., `model-serving:v1.0.0-abc123de`). Short commit SHA also included in `/health` response for audit trail.
- **Version Mismatch:** If `model.joblib` version (inferred from file mtime or explicit metadata) doesn't match expected `MODEL_VERSION`, startup fails with a clear error log.

### 2. Observability
**Per-Request Logging** (at INFO level by default):
- `request_id`: UUID generated per request (also sent back in response headers as `X-Request-ID`).
- `timestamp`: ISO 8601 timestamp of request arrival.
- `method` and `endpoint`: e.g., `POST /predict`.
- `input_shape`: feature count and shape confirmation (e.g., "5 fields received").
- `latency_ms`: end-to-end request processing time.
- `status_code`: HTTP response status.
- `error_code` (if applicable): e.g., `"missing_required_field"`.

**Example Log Line:**
```
[2025-01-15 10:30:45.123] [request_id=550e8400-e29b-41d4-a716-446655440000] [endpoint=POST /predict] [input_shape=5] [latency_ms=45] [status_code=200]
```

**Log Levels:**
- DEBUG: Model load details, request parsing steps.
- INFO: All successful predictions, health checks.
- WARNING: Slow requests (> 5s), model predictions with extreme input values.
- ERROR: Failed predictions, startup failures, missing model artifact.

### 3. Resource Limits
- **Max Request Payload Size:** 1 MB (enforced by FastAPI middleware).
- **Request Timeout:** 30 seconds total per request (enforced by ASGI server).
- **Connection Timeout:** 10 seconds (TCP handshake timeout).
- **Worker Processes:** 4 (for production, configurable via `WORKERS` environment variable).
- **Concurrent Request Limit:** 100 (enforced by uvicorn connection queue).

### 4. Configuration
All environment-driven configuration (no hardcoded environment-specific values):
- `MODEL_PATH`: Path to `model.joblib` (default: `"./model.joblib"`).
- `LOG_LEVEL`: Logging verbosity (default: `"INFO"`); valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`.
- `PORT`: Service listen port (default: `8080`).
- `HOST`: Service bind address (default: `"0.0.0.0"`).
- `WORKERS`: Number of uvicorn worker processes (default: `4`).
- `MODEL_VERSION`: Model semantic version for `/health` response (default: `"1.0.0"`).
- `CORS_ALLOWED_ORIGINS`: Comma-separated list of allowed origins for CORS (default: `"localhost:3000"` — explicitly restrictive).

Validation: Service startup fails with clear error if `MODEL_PATH` does not exist or is not readable.

### 5. Startup Behavior
- **Model Load:** On startup, attempt to load `model.joblib` via `joblib.load(MODEL_PATH)`. If load fails (file not found, corrupted, wrong version):
  - Log ERROR with stack trace.
  - Exit with status code 1 (do not start serving traffic).
  - `/health` will not be reachable; orchestration (e.g., Kubernetes) will detect startup failure.
- **Readiness Check:** After successful model load, service is ready to accept traffic. No warming-up requests required.
- **Graceful Shutdown:** On SIGTERM, drain in-flight requests (up to 30s timeout), then exit with status 0.

---

## Security Baseline

### 1. No Secrets in Code or Image
- No API keys, database credentials, or authentication tokens hardcoded in source.
- Model artifact (`model.joblib`) is not sensitive — it's a trained model, not a credential.
- All environment-specific configuration via environment variables, never in `.py` files.
- `.dockerignore` excludes `.git`, `.env`, `*.pem`, `*.key`, `credentials.json`, and any test data.

### 2. CORS Policy
- **Restrictive by Default:** `CORS_ALLOWED_ORIGINS` environment variable defaults to `"localhost:3000"` (development localhost only).
- **Production Override:** Must be explicitly set to production domain(s) at container runtime, e.g., `CORS_ALLOWED_ORIGINS="https://api.example.com"`.
- **Allowed Methods:** `POST` (for `/predict`), `GET` (for `/health`). No `*`.
- **Allowed Headers:** `Content-Type`, `X-Request-ID`. No `*`.
- **Credentials:** Not allowed (Credentials=false).

### 3. Dependency Pinning Strategy
- `requirements.txt` pins all direct and transitive dependencies to exact versions (e.g., `pandas==3.0.6`, not `pandas>=2.2`).
- Security updates to dependencies are staged: dependency authors are monitored, updates are tested in a staging environment, then merged to main with a dated commit message referencing the CVE (if applicable).
- Dockerfile uses multi-stage build with `python:3.13-slim` as base (minimal layer, excludes build tools from final image).

### 4. Docker Image Security
- **Non-Root User:** Service runs as unprivileged user `appuser` (UID 1000). Model loading and prediction do not require root.
- **Final Image:** `python:3.13-slim` base, only runtime dependencies, no development headers or compilers.
- **Read-Only Filesystem:** Model artifact and code copied as read-only (via Docker COPY, no volume mounts for code in production).
- **No Privileged Capabilities:** Standard container, no `--cap-add`, no `--privileged` mode.

### 5. Input Validation (Defense-in-Depth)
- **Type Checking:** Pydantic models enforce exact types at the API boundary before model.predict() is called.
- **Range Validation:** All numeric fields checked against min/max bounds before prediction.
- **Null Handling:** Null/missing fields rejected with 422 Unprocessable Entity before model sees them.
- **Attribute Order:** DataFrame column order validated to match training order (`sqft, bedrooms, bathrooms, age_years, location_score`) — prevents silent mis-prediction from wrong input order.

---

## Next Steps
`spec.md` is ready for review. Once approved, the implementation will proceed with:
1. **Step 2:** FastAPI wrapper, Dockerfile, CI/CD pipeline
2. **Step 3:** Automated tests (unit and integration)
3. **Step 4:** Self-review and deployment hand-off
