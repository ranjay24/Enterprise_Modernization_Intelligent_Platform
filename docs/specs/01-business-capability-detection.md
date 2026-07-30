# Business Capability Detection

## Problem
Business Capability Map shows 0 capabilities even though app has multiple domains.

## Solution
Analyze Controllers + Services + Entities + Repositories together. Group into domains: User Management, Course Management, Employee Management, Inquiry Management, Follow-Up Management, Orders, Payments, Feedback.

## Files to modify
- backend/app/services/analysis_engine.py
- backend/app/ai/service.py
- backend/app/pipeline/stages/enterprise_analysis.py
- frontend/src/components/results/BusinessCapabilityMap.tsx

## Acceptance Criteria
BusinessCapabilityMap shows at least 5 populated capabilities per project.

## Estimated Effort
2 weeks
