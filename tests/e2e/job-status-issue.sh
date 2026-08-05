#!/bin/bash

# Diagnostic test for: Job stays "Running" after code generation
# Issue: After generating code in Modernization Studio and returning to /jobs page,
#        job still shows as "Running"/"Queued" instead of "Completed"

API="http://localhost:8000/api"
COLOR_GREEN='\033[0;32m'
COLOR_RED='\033[0;31m'
COLOR_YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "Job Status Issue Diagnostic"
echo "=========================================="
echo ""

# Get latest job
JOBS_ID=$(curl -s "$API/jobs" | grep -o '"job_id":"[^"]*"' | head -1 | sed 's/"job_id":"\([^"]*\)"/\1/')

if [ -z "$JOBS_ID" ]; then
  echo -e "${RED}✗ No jobs found${NC}"
  exit 1
fi

echo "Job ID: $JOBS_ID"
echo ""

# ========== Check 1: Job Database Status ==========
echo -e "${YELLOW}Check 1: Database Job Status${NC}"
JOB_DATA=$(curl -s "$API/results/$JOBS_ID")
JOB_DB_STATUS=$(echo "$JOB_DATA" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "  Database status: $JOB_DB_STATUS"

case $JOB_DB_STATUS in
  "generation_complete") echo -e "  ${GREEN}✓ Should be in Completed section${NC}" ;;
  "generating") echo -e "  ${RED}✗ Still says 'generating' - DB not updated!${NC}" ;;
  "analysis_complete") echo -e "  ${YELLOW}⊙ Analysis done, waiting for code gen${NC}" ;;
  *) echo -e "  ${YELLOW}⊙ Status: $JOB_DB_STATUS${NC}" ;;
esac
echo ""

# ========== Check 2: Codegen Status Endpoint ==========
echo -e "${YELLOW}Check 2: Codegen Status Endpoint${NC}"
CODEGEN_STATUS=$(curl -s "$API/codegen/$JOBS_ID/status")
IN_PROGRESS=$(echo "$CODEGEN_STATUS" | grep -o '"in_progress":true' | wc -l)
PROGRESS=$(echo "$CODEGEN_STATUS" | grep -o '"progress":[0-9]*' | head -1 | cut -d':' -f2)
CURRENT_STAGE=$(echo "$CODEGEN_STATUS" | grep -o '"current_stage":"[^"]*"' | head -1 | cut -d'"' -f4)
SUMMARY=$(echo "$CODEGEN_STATUS" | grep -o '"status":"[^"]*"' | head -2 | tail -1 | cut -d'"' -f4)

echo "  In Progress: $([ $IN_PROGRESS -eq 0 ] && echo -e "${GREEN}false (Complete)${NC}" || echo -e "${RED}true (Still Running)${NC}")"
echo "  Progress: $PROGRESS%"
echo "  Current Stage: $CURRENT_STAGE"
echo "  Summary Status: $SUMMARY"
echo ""

# ========== Check 3: Artifact Existence ==========
echo -e "${YELLOW}Check 3: Generated Artifacts in Database${NC}"

ARCH=$(curl -s -o /dev/null -w "%{http_code}" "$API/codegen/$JOBS_ID/architecture")
PLAN=$(curl -s -o /dev/null -w "%{http_code}" "$API/codegen/$JOBS_ID/plan")
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API/codegen/$JOBS_ID/code")
REVIEW=$(curl -s -o /dev/null -w "%{http_code}" "$API/codegen/$JOBS_ID/review")

echo "  Architecture: $([ $ARCH -eq 200 ] && echo -e "${GREEN}✓ 200${NC}" || echo -e "${RED}✗ $ARCH${NC}")"
echo "  Plan: $([ $PLAN -eq 200 ] && echo -e "${GREEN}✓ 200${NC}" || echo -e "${RED}✗ $PLAN${NC}")"
echo "  Code: $([ $CODE -eq 200 ] && echo -e "${GREEN}✓ 200${NC}" || echo -e "${RED}✗ $CODE${NC}")"
echo "  Review: $([ $REVIEW -eq 200 ] && echo -e "${GREEN}✓ 200${NC}" || echo -e "${RED}✗ $REVIEW${NC}")"
echo ""

# ========== Check 4: Services Generated Count ==========
echo -e "${YELLOW}Check 4: Code Generation Results${NC}"
SERVICES=$(curl -s "$API/codegen/$JOBS_ID/code" | grep -o '"service[^,]*":' | wc -l)
SERVICES_IN_STATUS=$(echo "$CODEGEN_STATUS" | grep -o '"services_generated":\[[^]]*\]' | grep -o '"[^"]*Service"' | wc -l)

echo "  Services generated (code endpoint): $SERVICES"
echo "  Services in status: $SERVICES_IN_STATUS"

if [ $SERVICES -gt 0 ]; then
  echo -e "  ${GREEN}✓ Code has been generated${NC}"
else
  echo -e "  ${RED}✗ No services generated${NC}"
fi
echo ""

# ========== ROOT CAUSE ANALYSIS ==========
echo -e "${YELLOW}Root Cause Analysis:${NC}"
echo ""

if [ "$JOB_DB_STATUS" = "generating" ] && [ $IN_PROGRESS -eq 0 ] && [ $SERVICES -gt 0 ]; then
  echo -e "${RED}✗ ISSUE CONFIRMED:${NC}"
  echo "  - Database still says 'generating'"
  echo "  - But codegen endpoint says 'in_progress: false'"
  echo "  - And services ARE generated"
  echo ""
  echo "ROOT CAUSE: Job DB status NOT updated after code generation completes"
  echo ""
  echo "FIX NEEDED:"
  echo "  - Orchestrator completes but doesn't call job_repo.update_job() correctly"
  echo "  - OR frontend polling isn't triggering the status endpoint update"
  echo ""
  echo "WORKAROUND: Manually refresh /jobs page - should update within 2 seconds"

elif [ "$JOB_DB_STATUS" = "generation_complete" ]; then
  echo -e "${GREEN}✓ STATUS CORRECT:${NC}"
  echo "  - Job DB status is 'generation_complete'"
  echo "  - Should appear in Completed section on /jobs page"
  echo "  - If still showing as Running, it's a FRONTEND CACHING ISSUE"
  echo ""
  echo "FRONTEND ISSUE:"
  echo "  - Check React Query staleTime setting"
  echo "  - Verify polling interval is working"
  echo "  - Clear browser cache and refresh"

else
  echo -e "${YELLOW}⊙ UNCERTAIN STATE:${NC}"
  echo "  Database status: $JOB_DB_STATUS"
  echo "  This may be expected if code generation still in progress"
fi

echo ""
echo "=========================================="
echo "Recommendation:"
echo "=========================================="

if [ "$JOB_DB_STATUS" != "generation_complete" ] && [ $SERVICES -gt 0 ]; then
  echo "1. Restart backend to sync database state"
  echo "2. Or wait 30 seconds and refresh /jobs page"
  echo "3. Status should update within 2 seconds of refresh"
else
  echo "1. Clear browser cache (DevTools → Application → Clear cache)"
  echo "2. Hard refresh (Ctrl+Shift+R)"
  echo "3. Check browser console for errors"
fi
