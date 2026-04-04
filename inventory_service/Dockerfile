FROM python:3.12-slim
WORKDIR /app
COPY inventory_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY inventory_service/ .
COPY shared/ /app/shared/
ENV PYTHONPATH=/app
CMD ["sh", "-c", "alembic -c migrations/alembic.ini upgrade head && uvicorn main:app --host 0.0.0.0 --port 8002"]
