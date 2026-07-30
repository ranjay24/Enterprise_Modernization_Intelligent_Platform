# Microservice Recommendations

## Problem
No extraction recommendations generated.

## Solution
For each candidate service provide: business purpose, APIs, database tables, dependencies, migration complexity, risk, effort, suggested wave.

## Files to modify
- backend/app/pipeline/stages/ai_migration.py
- backend/app/ai/service.py
- frontend/src/components/results/MicroserviceRecommendations.tsx

## Acceptance Criteria
Each recommendation has all 8 fields populated.

## Estimated Effort
2 weeks
