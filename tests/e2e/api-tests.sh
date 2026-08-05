#!/bin/bash

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API="http://localhost:8000"
RESULTS_DIR="./tests/e2e/results"
mkdir -p "$RESULTS_DIR"

echo "========================================"
echo "EMIP End-to-End API Tests"
echo "========================================"
echo ""

# Test counters
PASSED=0
FAILED=0

test_api() {
  local name=$1
  local method=$2
  local endpoint=$3
  local expected_status=$4

  echo -n "Testing: $name ... "

  response=$(curl -s -w "\n%{http_code}" -X "$method" "$API$endpoint")
  body=$(echo "$response" | head -n -1)
  status=$(echo "$response" | tail -n 1)

  if [ "$status" = "$expected_status" ]; then
    echo -e "${GREEN}✓ OK ($status)${NC}"
    ((PASSED++))
    echo "$body" > "$RESULTS_DIR/${name// /_}.json"
  else
    echo -e "${RED}✗ FAILED (got $status, expected $expected_status)${NC}"
    ((FAILED++))
  fi
  echo ""
}

# ========== Phase 1: List Jobs ==========
echo -e "${YELLOW}Phase 1: List Jobs${NC}"
test_api "List all jobs" "GET" "/jobs" "200"

# ========== Phase 2: Get recent job ==========
echo -e "${YELLOW}Phase 2: Get Latest Job${NC}"
JOBS=$(curl -s "$API/jobs" | grep -o '"job_id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$JOBS" ]; then
  echo -e "${YELLOW}No jobs found. Please run an analysis first.${NC}"
  exit 0
fi

echo "Using Job ID: $JOBS"
test_api "Get job status" "GET" "/results/$JOBS" "200"

# ========== Phase 3: Analysis Results ==========
echo -e "${YELLOW}Phase 3: Analysis Results${NC}"
test_api "Get analysis results" "GET" "/results/$JOBS/analysis" "200"

# Extract data
RESULTS=$(curl -s "$API/results/$JOBS/analysis")
BOUNDARIES=$(echo "$RESULTS" | grep -o '"service_boundaries"' | wc -l)
COST=$(echo "$RESULTS" | grep -o '"cost_comparison"' | wc -l)

echo "Analysis contains:"
echo "  - Service boundaries: $([ $BOUNDARIES -gt 0 ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo "  - Cost data: $([ $COST -gt 0 ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo ""

# ========== Phase 4: Code Generation APIs ==========
echo -e "${YELLOW}Phase 4: Code Generation APIs${NC}"
test_api "Codegen status" "GET" "/codegen/$JOBS/status" "200"
test_api "Architecture design" "GET" "/codegen/$JOBS/architecture" "200"
test_api "Service plan" "GET" "/codegen/$JOBS/plan" "200"
test_api "Code review" "GET" "/codegen/$JOBS/review" "200"

# Parse codegen status
CODEGEN_STATUS=$(curl -s "$API/codegen/$JOBS/status")
IN_PROGRESS=$(echo "$CODEGEN_STATUS" | grep -o '"in_progress":true' | wc -l)
SERVICES_GEN=$(echo "$CODEGEN_STATUS" | grep -o '"services_generated"' | wc -l)

echo "Code Generation Status:"
echo "  - In Progress: $([ $IN_PROGRESS -eq 0 ] && echo -e "${GREEN}✓ Complete${NC}" || echo -e "${YELLOW}⊙ Running${NC}")"
echo "  - Services Generated: $([ $SERVICES_GEN -gt 0 ] && echo -e "${GREEN}✓ Yes${NC}" || echo -e "${RED}✗ No${NC}")"
echo ""

# ========== Phase 5: Get first service code ==========
echo -e "${YELLOW}Phase 5: Service Code Generation${NC}"
test_api "Get all services code" "GET" "/codegen/$JOBS/code" "200"

# ========== Phase 6: Job Status Progression ==========
echo -e "${YELLOW}Phase 6: Job Status Flow${NC}"
JOB_DATA=$(curl -s "$API/results/$JOBS")
JOB_STATUS=$(echo "$JOB_DATA" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)

echo "Job Status: $JOB_STATUS"
case $JOB_STATUS in
  "analysis_complete") echo -e "  ${GREEN}✓ Analysis Complete${NC}" ;;
  "generation_complete") echo -e "  ${GREEN}✓ Code Generation Complete${NC}" ;;
  "generating") echo -e "  ${YELLOW}⊙ Generating Code${NC}" ;;
  "analyzing") echo -e "  ${YELLOW}⊙ Analyzing${NC}" ;;
  *) echo -e "  ${RED}✗ Unknown Status: $JOB_STATUS${NC}" ;;
esac
echo ""

# ========== Phase 7: Data Integrity ==========
echo -e "${YELLOW}Phase 7: Data Integrity Checks${NC}"

# Check results have required fields
ANALYSIS=$(curl -s "$API/results/$JOBS/analysis")
HAS_SERVICES=$(echo "$ANALYSIS" | grep -q "service_boundaries" && echo "1" || echo "0")
HAS_MIGRATION=$(echo "$ANALYSIS" | grep -q "migration_waves" && echo "1" || echo "0")
HAS_COST=$(echo "$ANALYSIS" | grep -q "cost_comparison" && echo "1" || echo "0")

echo "Analysis Data:"
echo "  - Service Boundaries: $([ $HAS_SERVICES -eq 1 ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo "  - Migration Waves: $([ $HAS_MIGRATION -eq 1 ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo "  - Cost Comparison: $([ $HAS_COST -eq 1 ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
echo ""

# ========== Summary ==========
TOTAL=$((PASSED + FAILED))
echo "========================================"
echo "Test Summary"
echo "========================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: $([ $FAILED -eq 0 ] && echo -e "${GREEN}$FAILED${NC}" || echo -e "${RED}$FAILED${NC}")"
echo "Total:  $TOTAL"
echo ""

if [ $FAILED -eq 0 ]; then
  echo -e "${GREEN}✓ All tests passed!${NC}"
  exit 0
else
  echo -e "${RED}✗ Some tests failed${NC}"
  exit 1
fi
