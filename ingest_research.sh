#!/bin/bash

# BloomNet Data Ingestion Script
# Uploads sample data to the research mart for testing

BASE_URL="http://localhost:8201"  # research-parent
AUTH_TOKEN="${RESEARCH_PARENT_TOKEN}"

if [ -z "$AUTH_TOKEN" ]; then
    echo "Error: RESEARCH_PARENT_TOKEN not set in environment"
    echo "Please set the token in your .env file"
    exit 1
fi

echo "🔬 BloomNet Research Mart Data Ingestion"
echo "========================================"
echo "Uploading research data to the research mart..."
echo ""

# Function to upload a file
upload_file() {
    local file_path=$1
    local file_name=$(basename "$file_path")

    echo "📄 Uploading: $file_name"

    response=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -F "file=@$file_path" \
        -F "key=$file_name" \
        "$BASE_URL/write")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" -eq 200 ]; then
        echo "✅ Upload successful: $file_name"
        echo "📄 Response: $body"
    else
        echo "❌ Upload failed: $file_name (HTTP $http_code)"
        echo "📄 Error: $body"
    fi
    echo ""
}

# Upload all research data
for file in data/sample-research/*; do
    if [ -f "$file" ]; then
        upload_file "$file"
    fi
done

echo "🎉 Research mart ingestion complete!"
echo ""
echo "🔍 You can now check replication by querying:"
echo "   curl http://localhost:8201/inventory | jq ."
echo "   curl http://localhost:8202/inventory | jq ."
echo "   curl http://localhost:8203/inventory | jq ."
