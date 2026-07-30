# Service Boundary Detection (DDD-based)

## Problem
Boundaries based only on package names.

## Solution
DDD-based detection chain: Controllers → Services → Repositories → Entities → Dependencies → Business Capability → Microservice Candidate.

## Files to modify
- backend/app/pipeline/stages/ai_boundaries.py
- backend/app/ai/service.py
- backend/app/ai/orchestrator.py

## Acceptance Criteria
Boundaries reflect actual business domains, not just package folders.

## Estimated Effort
2 weeks
