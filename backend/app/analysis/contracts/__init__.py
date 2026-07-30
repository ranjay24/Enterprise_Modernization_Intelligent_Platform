"""Analysis engine contracts — reusable interfaces for the plugin architecture."""

from app.analysis.contracts.analyzer import Analyzer, AnalyzerMetadata
from app.analysis.contracts.context import AnalysisContext
from app.analysis.contracts.result import AnalysisResult

__all__ = ["AnalysisContext", "AnalysisResult", "Analyzer", "AnalyzerMetadata"]
