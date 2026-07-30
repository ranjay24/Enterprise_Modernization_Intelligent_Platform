# Confidence Calculation

## Problem
Overall 75% confidence is opaque.

## Solution
Multi-factor: static analysis completeness, dependency confidence, business capability confidence, AI reasoning confidence, missing info penalty.

## Files to modify
- backend/app/pipeline/stages/results_assembly.py
- frontend/src/components/results/ConfidenceCenter.tsx
- frontend/src/types/results.ts

## Acceptance Criteria
Confidence shows 5-factor breakdown, not a single number.

## Estimated Effort
1 week
