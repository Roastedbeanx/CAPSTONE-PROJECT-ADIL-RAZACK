FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /app/requirements.txt

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /install /usr/local
COPY datasets /app/datasets
COPY solutions/submissions/adil_razack/02_sql_and_viz/etl_full.py /app/solutions/submissions/adil_razack/02_sql_and_viz/etl_full.py

ENV DATA_DIR=/app/datasets
ENV OUTPUT_DIR=/app/outputs/results/adil_razack/02_sql_and_viz

RUN mkdir -p /app/outputs
ENTRYPOINT ["python", "/app/solutions/submissions/adil_razack/02_sql_and_viz/etl_full.py"]
