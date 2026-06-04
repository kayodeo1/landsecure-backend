FROM python:3.12-slim

WORKDIR /app

# psycopg[binary] adds the PostgreSQL driver for the PostGIS production path
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg[binary]==3.2.3

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
