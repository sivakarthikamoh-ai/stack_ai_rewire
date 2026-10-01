import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.schema import FEATURES, PredictionRequest

MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0.0")
API_VERSION = "1.0.0"
MODEL_PATH = os.getenv("MODEL_PATH", "./model.joblib")
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "localhost:3000")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("house-price-api")


class APIError(Exception):
    def __init__(self, error: str, field: str | None, detail: str, status_code: int = 400):
        self.error = error
        self.field = field
        self.detail = detail
        self.status_code = status_code


def error_response(error: str, field: str | None, detail: str, status_code: int):
    return JSONResponse(
        status_code=status_code,
        content={"error": error, "field": field, "detail": detail},
    )


def _field_name_from_loc(loc: tuple[Any, ...]) -> str | None:
    for part in reversed(loc):
        if isinstance(part, str):
            return part
    return None


def _extract_validation_error(exc: ValidationError) -> tuple[str, str | None, str, int]:
    errors = exc.errors()
    if not errors:
        return ("invalid_input", None, "Request body is invalid", 422)

    first = errors[0]
    field = _field_name_from_loc(first.get("loc", ()))
    error_type = first.get("type", "value_error")
    if "missing" in error_type:
        return ("missing_required_field", field, f"Field '{field}' is required", 422)
    if (
        "int_parsing" in error_type
        or "float_parsing" in error_type
        or "string_type" in error_type
        or "int_type" in error_type
        or "float_type" in error_type
    ):
        return ("invalid_type", field, f"Field '{field}' must be a number, got {first.get('input')!r}", 422)
    if "greater" in error_type or "less" in error_type or "not_ge" in error_type or "not_le" in error_type:
        return ("out_of_range", field, f"Field '{field}' is out of range", 422)
    return ("invalid_input", field, first.get("msg", "Request body is invalid"), 422)


def _get_model() -> Any:
    model = joblib.load(MODEL_PATH)
    return model


def _ensure_model_loaded() -> Any:
    if not hasattr(app.state, "model") or app.state.model is None:
        try:
            app.state.model = _get_model()
            logger.info("Model loaded successfully from %s", MODEL_PATH)
        except Exception:
            logger.exception("Model failed to load: %s", MODEL_PATH)
            raise APIError(
                "model_load_failed",
                None,
                "Model artifact failed to load: model.joblib not found or corrupted",
                503,
            )
    return app.state.model


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.model = _get_model()
        logger.info("Model loaded successfully from %s", MODEL_PATH)
        yield
    except Exception:
        logger.exception("Model failed to load: %s", MODEL_PATH)
        raise


app = FastAPI(title="House Price Predictor", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ALLOWED_ORIGINS.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "X-Request-ID"],
)


@app.exception_handler(APIError)
async def api_exception_handler(_: Request, exc: APIError):
    return error_response(exc.error, exc.field, exc.detail, exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    field = _field_name_from_loc(exc.errors()[0].get("loc", ()))
    error_type = exc.errors()[0].get("type", "value_error")
    if "missing" in error_type:
        return error_response("missing_required_field", field, f"Field '{field}' is required", 422)
    if (
        "int_parsing" in error_type
        or "float_parsing" in error_type
        or "int_type" in error_type
        or "float_type" in error_type
    ):
        return error_response("invalid_type", field, f"Field '{field}' must be a number", 422)
    return error_response("invalid_input", field, exc.errors()[0].get("msg", "Request body is invalid"), 422)


@app.middleware("http")
async def add_request_metadata(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_id=%s method=%s path=%s status=%s latency_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/health")
async def health() -> dict[str, Any]:
    try:
        _ensure_model_loaded()
    except APIError as exc:
        return JSONResponse(status_code=exc.status_code, content={"status": "unhealthy", "detail": exc.detail})

    return {
        "status": "healthy",
        "model_version": MODEL_VERSION,
        "api_version": API_VERSION,
        "commit_sha": os.getenv("COMMIT_SHA", "unknown"),
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


@app.post(
    "/predict",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": PredictionRequest.model_json_schema()}
            },
        }
    },
)
async def predict(request: Request):
    raw_body = await request.body()
    if not raw_body:
        raise APIError("empty_payload", None, "Request body cannot be empty", 400)
    if len(raw_body) > 1024 * 1024:
        raise APIError("payload_too_large", None, "Request body exceeds maximum size of 1MB", 413)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise APIError("malformed_json", None, "Request body is not valid JSON", 400)

    if payload is None:
        raise APIError("empty_payload", None, "Request body cannot be empty", 400)
    if not isinstance(payload, dict):
        raise APIError("invalid_input", None, "Request body must be a JSON object", 400)

    try:
        validated = PredictionRequest(**payload)
    except ValidationError as exc:
        error, field, detail, status = _extract_validation_error(exc)
        raise APIError(error, field, detail, status) from exc

    model = _ensure_model_loaded()
    dataframe = pd.DataFrame([validated.model_dump()], columns=FEATURES)
    prediction = float(model.predict(dataframe)[0])
    return {"predicted_price": prediction, "currency": "USD", "model_version": MODEL_VERSION}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
        workers=int(os.getenv("WORKERS", "1")),
    )
