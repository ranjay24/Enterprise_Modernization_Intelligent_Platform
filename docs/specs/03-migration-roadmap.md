# Migration Roadmap

## Problem
Waves are package-based with no justification.

## Solution
Generate waves based on business domains, dependency graph, database coupling, shared entities, API dependencies, risk analysis.

## Files to modify
- backend/app/pipeline/stages/ai_migration.py
- backend/app/ai/service.py

## Acceptance Criteria
Waves have clear business + technical justification.

## Estimated Effort
2 weeks
