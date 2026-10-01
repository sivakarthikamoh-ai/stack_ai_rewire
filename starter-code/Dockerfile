FROM python:3.13-slim AS builder

WORKDIR /build
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.13-slim AS runtime

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HOST=0.0.0.0 \
    PORT=8080 \
    WORKERS=4 \
    MODEL_PATH=/app/model.joblib \
    LOG_LEVEL=INFO \
    MODEL_VERSION=1.0.0 \
    CORS_ALLOWED_ORIGINS=localhost:3000

COPY --from=builder /install /usr/local
COPY app ./app
COPY model.joblib ./model.joblib

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin appuser && \
    chown -R appuser:appuser /app

USER appuser
EXPOSE 8080

CMD ["sh", "-c", "python -m uvicorn app.main:app --host ${HOST} --port ${PORT} --workers ${WORKERS}"]
