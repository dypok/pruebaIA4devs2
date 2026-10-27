FROM apache/airflow:2.9.3-python3.11

USER root

# Herramientas de sistema ligeras (sin Java ni JVM)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       procps \
       curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
