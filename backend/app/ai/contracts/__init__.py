"""AI contracts — strongly typed interfaces for the AI intelligence layer."""

from app.ai.contracts.adr import (
    ADRConsequence,
    ADROption,
    ADRStatus,
    ADRTradeoff,
    AIDecisionRecord,
)
from app.ai.contracts.developer import (
    AIDeveloperReport,
    ArchitectureFinding,
    AWSServiceRecommendation,
    CodeQualityAssessment,
    DependencyAnalysis,
    MigrationOpportunity,
    TechnicalDebtItem,
)
from app.ai.contracts.executive import (
    AIExecutiveSummary,
    BusinessRisk,
    CloudReadinessAssessment,
    CostImpact,
    ExecutiveRecommendation,
)
from app.ai.contracts.migration import (
    AIMigrationPlan,
    AIMigrationService,
    AIMigrationWave,
    EffortEstimate,
    MigrationPhase,
)
from app.ai.contracts.recommendation import (
    AIRecommendation,
    EvidenceSource,
    ExplainabilityData,
    ReasoningChain,
    RecommendationCategory,
    RecommendationPriority,
)

__all__ = [
    "ADRConsequence",
    "ADROption",
    "ADRStatus",
    "ADRTradeoff",
    "AIDecisionRecord",
    "AIDeveloperReport",
    "AIExecutiveSummary",
    "AIMigrationPlan",
    "AIMigrationService",
    "AIMigrationWave",
    "AIRecommendation",
    "AWSServiceRecommendation",
    "ArchitectureFinding",
    "BusinessRisk",
    "CloudReadinessAssessment",
    "CodeQualityAssessment",
    "CostImpact",
    "DependencyAnalysis",
    "EffortEstimate",
    "EvidenceSource",
    "ExecutiveRecommendation",
    "ExplainabilityData",
    "MigrationOpportunity",
    "MigrationPhase",
    "ReasoningChain",
    "RecommendationCategory",
    "RecommendationPriority",
    "TechnicalDebtItem",
]
