FROM python:3.11-slim

# Use Alibaba Cloud mirror for faster apt in China
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# Install postgres client libs for asyncpg build
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8848

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8848"]