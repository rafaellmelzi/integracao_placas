FROM python:3.12-slim-bookworm

WORKDIR /app

# Upgrade pip and install python dependencies (psycopg2-binary provides pre-compiled PostgreSQL driver)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
