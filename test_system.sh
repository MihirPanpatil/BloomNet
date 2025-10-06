#!/bin/bash

# BloomNet System Testing Script
# Tests all components and functionality

echo "🧪 BloomNet System Testing"
echo "=========================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name=$1
    local command=$2
    local expected_code=${3:-0}

    TESTS_RUN=$((TESTS_RUN + 1))
    echo -n "🔍 $test_name... "

    # Run the command and capture output
    output=$(eval "$command" 2>&1)
    exit_code=$?

    if [ $exit_code -eq $expected_code ]; then
        echo -e "${GREEN}✅ PASSED${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        echo "   Command: $command"
        echo "   Exit code: $exit_code (expected: $expected_code)"
        echo "   Output: $output"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Function to check if a service is responding
check_service() {
    local url=$1
    local service_name=$2

    run_test "Check $service_name health" \
        "curl -s -o /dev/null -w '%{http_code}' '$url'" \
        200
}

echo "📋 Running System Tests..."
echo "=========================="

# Test 1: Check if Docker containers are running
echo ""
echo "🐳 Docker Services Test"
echo "-----------------------"
run_test "Docker compose is running" \
    "docker compose ps | grep -q 'Up'" \
    0

# Test 2: Check individual services
echo ""
echo "🔧 Service Health Tests"
echo "-----------------------"
check_service "http://localhost:8001/health" "Kernel 1"
check_service "http://localhost:8002/health" "Kernel 2"
check_service "http://localhost:8003/health" "Kernel 3"
check_service "http://localhost:8101/health" "Photos Parent"
check_service "http://localhost:8201/health" "Research Parent"
check_service "http://localhost:8301/health" "Clients Parent"
check_service "http://localhost:3000" "Portal"

# Test 3: Check MinIO
echo ""
echo "📦 Storage Tests"
echo "----------------"
run_test "MinIO API accessible" \
    "curl -s -o /dev/null -w '%{http_code}' 'http://localhost:9000/minio/health/ready'" \
    200

# Test 4: Test kernel registry
echo ""
echo "🗂️ Registry Tests"
echo "------------------"
run_test "Kernel 1 registry accessible" \
    "curl -s 'http://localhost:8001/registry' | jq -e '.marts' > /dev/null" \
    0

# Test 5: Test data upload (if sample data exists)
echo ""
echo "📤 Data Upload Tests"
echo "--------------------"
if [ -f "data/sample-photos/sample_photo_001.txt" ]; then
    run_test "Photos mart accepts uploads" \
        "curl -s -w '%{http_code}' -X POST -H 'Authorization: Bearer $PHOTOS_PARENT_TOKEN' -F 'file=@data/sample-photos/sample_photo_001.txt' -F 'key=test_upload.txt' 'http://localhost:8101/write' | grep -q 200" \
        0
else
    echo -e "${YELLOW}⚠️  Sample data not found - skipping upload test${NC}"
fi

# Test 6: Check portal API endpoints
echo ""
echo "🌐 Portal API Tests"
echo "-------------------"
run_test "Portal registry API" \
    "curl -s 'http://localhost:3000/api/registry' | jq -e '.' > /dev/null" \
    0

# Test 7: Check inter-service communication
echo ""
echo "🔗 Network Tests"
echo "----------------"
run_test "Kernel-to-kernel communication" \
    "curl -s 'http://localhost:8002/registry' | jq -e '.kernels' > /dev/null" \
    0

# Summary
echo ""
echo "📊 Test Summary"
echo "==============="
echo "Total tests run: $TESTS_RUN"
echo -e "✅ Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "❌ Failed: ${RED}$TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 All tests passed! Your BloomNet system is working correctly.${NC}"
    echo ""
    echo "🚀 Next steps:"
    echo "   1. Run data ingestion: ./ingest_all.sh"
    echo "   2. Check replication: curl http://localhost:8101/inventory | jq ."
    echo "   3. Access portal: http://localhost:3000"
    echo "   4. Check MinIO: http://localhost:9001"
else
    echo ""
    echo -e "${RED}⚠️  Some tests failed. Check the output above for details.${NC}"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "   1. Check container logs: docker compose logs"
    echo "   2. Verify .env tokens are correct"
    echo "   3. Restart services: docker compose restart"
fi

exit $TESTS_FAILED
