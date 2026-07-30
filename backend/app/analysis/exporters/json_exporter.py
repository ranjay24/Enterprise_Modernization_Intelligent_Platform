"""JSON Exporter — serializes AnalysisResult to JSON."""

from __future__ import annotations

import json

from app.analysis.contracts.result import AnalysisResult


class JSONExporter:
    def export(self, result: AnalysisResult) -> str:
        return json.dumps(result.to_dict(), indent=2, default=str)

    def export_dict(self, result: AnalysisResult) -> dict:
        return result.to_dict()
