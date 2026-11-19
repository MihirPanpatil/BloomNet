#!/bin/bash

# BloomNet Complete Data Ingestion Script
# Uploads sample data to all marts for comprehensive testing

echo "🌸 BloomNet Complete Data Ingestion"
echo "==================================="
echo "This script will upload sample data to all three marts:"
echo "  📸 Photos Mart (3 files)"
echo "  🔬 Research Mart (1 file)"
echo "  👥 Clients Mart (1 file)"
echo ""
echo "Make sure all services are running with:"
echo "  docker compose up -d"
echo ""

# Check if required environment variables are set
REQUIRED_TOKENS=(
    "PHOTOS_PARENT_TOKEN"
    "RESEARCH_PARENT_TOKEN"
    "CLIENTS_PARENT_TOKEN"
)

MISSING_TOKENS=()
for token in "${REQUIRED_TOKENS[@]}"; do
    if [ -z "${!token}" ]; then
        MISSING_TOKENS+=("$token")
    fi
done

if [ ${#MISSING_TOKENS[@]} -ne 0 ]; then
    echo "❌ Error: Missing required environment variables:"
    for token in "${MISSING_TOKENS[@]}"; do
        echo "   - $token"
    done
    echo ""
    echo "Please ensure these tokens are set in your .env file"
    exit 1
fi

echo "✅ All required tokens are configured"
echo ""

# Function to run ingestion with timing
run_ingestion() {
    local script=$1
    local mart_name=$2

    echo "🚀 Starting $mart_name ingestion..."
    echo "========================================"

    start_time=$(date +%s)
    if bash "$script"; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        echo "✅ $mart_name ingestion completed in ${duration}s"
    else
        echo "❌ $mart_name ingestion failed"
        exit 1
    fi
    echo ""
    echo "⏳ Waiting 5 seconds before next ingestion..."
    sleep 5
}

# Run ingestion for each mart
run_ingestion "./ingest_photos.sh" "Photos Mart"
run_ingestion "./ingest_research.sh" "Research Mart"
run_ingestion "./ingest_clients.sh" "Clients Mart"

echo "🎉 All data ingestion complete!"
echo "=============================="
echo ""
echo "🔍 Verification Commands:"
echo "   # Check photos mart replication"
echo "   curl http://localhost:8101/inventory | jq ."
echo "   curl http://localhost:8102/inventory | jq ."
echo "   curl http://localhost:8103/inventory | jq ."
echo ""
echo "   # Check research mart replication"
echo "   curl http://localhost:8201/inventory | jq ."
echo "   curl http://localhost:8202/inventory | jq ."
echo "   curl http://localhost:8203/inventory | jq ."
echo ""
echo "   # Check clients mart replication"
echo "   curl http://localhost:8301/inventory | jq ."
echo "   curl http://localhost:8302/inventory | jq ."
echo "   curl http://localhost:8303/inventory | jq ."
echo ""
echo "🌐 Access the portal at: http://localhost:3000"
echo "📊 Check MinIO at: http://localhost:9001 (log in with MINIO_ROOT_USER / MINIO_ROOT_PASSWORD from .env)"
