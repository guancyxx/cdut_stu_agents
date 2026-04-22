FROM python:3.11-slim

# Install postgres client libs for asyncpg build
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8848

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8848"]