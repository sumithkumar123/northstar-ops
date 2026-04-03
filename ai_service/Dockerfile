FROM python:3.12-slim
WORKDIR /app
COPY ai_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ai_service/ .
COPY shared/ /app/shared/
ENV PYTHONPATH=/app
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8004}"]
