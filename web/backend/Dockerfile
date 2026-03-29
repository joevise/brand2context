FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ && rm -rf /var/lib/apt/lists/*
COPY web/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY brand2context/ /app/brand2context/
COPY schema/ /app/schema/
COPY web/backend/ /app/
RUN mkdir -p /app/data /app/data/brands
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
