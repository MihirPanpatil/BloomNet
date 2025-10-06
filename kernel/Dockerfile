FROM python:3.11-slim
WORKDIR /app

# system deps for certs and networking tools
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

COPY ./app /app
RUN pip install --no-cache-dir fastapi uvicorn[standard] requests PyJWT minio==7.1.16 prometheus_client

COPY ./app/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
EXPOSE 8000
CMD ["/app/entrypoint.sh"]