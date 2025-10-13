FROM python:3.11-slim-bookworm
WORKDIR /app

# Copy requirements file first
COPY requirements.txt .

# Install build tools and Python dependencies, then clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        curl && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove \
        build-essential \
        python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY ./app /app
COPY ./app/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create data directory and set ownership
RUN mkdir -p /app/data && chown -R appuser:appuser /app

EXPOSE 8000
USER appuser
CMD ["/app/entrypoint.sh"]

