FROM python:3.12-slim
WORKDIR /app
# Build context is the repo root (set in docker-compose.yml)
COPY auth_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY auth_service/ .
COPY shared/ /app/shared/
COPY scripts/ /scripts/
ENV PYTHONPATH=/app
CMD ["sh", "-c", "alembic -c migrations/alembic.ini upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}"]
