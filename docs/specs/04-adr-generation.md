# ADR Generation

## Problem
ADRs are generic (not project-specific).

## Solution
Generate specific ADRs from actual analysis data — e.g., "Separate Payment Service due to Razorpay integration".

## Files to modify
- backend/app/pipeline/stages/ai_adrs.py
- backend/app/ai/service.py
- backend/app/ai/engine.py

## Acceptance Criteria
ADRs reference actual classes, endpoints, and dependencies from the project.

## Estimated Effort
1 week
