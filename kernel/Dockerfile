FROM python:3.11-slim
WORKDIR /app

# Install system dependencies and build tools in a single layer
# Then, install Python packages and remove build tools to keep the image slim
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    build-essential \
    python3-dev && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    apt-get purge -y --auto-remove build-essential python3-dev

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app
COPY ./app/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create data directory and set ownership
RUN mkdir -p /app/data && chown -R appuser:appuser /app

EXPOSE 8000
USER appuser
CMD ["/app/entrypoint.sh"]

