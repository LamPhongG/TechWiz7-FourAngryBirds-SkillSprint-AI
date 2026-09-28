FROM python:3.12-slim

WORKDIR /app

# Install system utilities needed for healthcheck and compiling packages if necessary
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application code, seed data, documents, and setup scripts
COPY backend /app/backend
COPY sample_documents /app/sample_documents
COPY role_matrix /app/role_matrix
COPY setup_database.py /app/setup_database.py
COPY backend/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/backend

EXPOSE 8000

ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
