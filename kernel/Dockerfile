FROM python:3.11-slim
WORKDIR /app

# system deps for certs and networking tools
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

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