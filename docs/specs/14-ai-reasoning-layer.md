# AI Reasoning Layer

## Problem
Reasoning relies on package structure only.

## Solution
Feed dependency graph → entity graph → business capability discovery → bounded context detection → service boundary detection → migration planning → ADR generation → cost & readiness.

## Files to modify
- backend/app/ai/engine.py
- backend/app/ai/orchestrator.py
- backend/app/pipeline/stages/ai_boundaries.py

## Acceptance Criteria
AI prompts include full dependency graph, entity map, and endpoint data.

## Estimated Effort
2 weeks
