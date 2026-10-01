# ✅ Stage 1 — Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#  Stage 2 — Final image
FROM python:3.11-slim

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy entire project
COPY . .

# Environment variables (Requirement 5)
ENV DATA_DIR=/app/datasets
ENV OUTPUT_DIR=/app/outputs/results/adil_razack/02_sql_and_viz

#  Run ETL automatically (Requirement 3)
ENTRYPOINT ["python", "solutions/submissions/adil_razack/02_sql_and_viz/etl_full.py"]
