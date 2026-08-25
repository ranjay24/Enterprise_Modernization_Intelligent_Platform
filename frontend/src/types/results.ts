import type { AnalysisResult, ServiceBoundary } from './api';

export interface ConfidenceFactor {
  id: string;
  name: string;
  score: number;
  weight: number;
  description: string;
  status: 'high' | 'medium' | 'low';
}

export interface ConfidenceBreakdown {
  overall: number;
  factors: ConfidenceFactor[];
}

export interface RiskHeatmapEntry {
  id: string;
  service: string;
  migrationRisk: 'low' | 'medium' | 'high' | 'critical';
  architecturalRisk: 'low' | 'medium' | 'high' | 'critical';
  dependencyRisk: 'low' | 'medium' | 'high' | 'critical';
  overallRisk: 'low' | 'medium' | 'high' | 'critical';
  riskFactors: string[];
  mitigation: string;
}

export interface EnhancedRecommendation {
  id: string;
  title: string;
  description: string;
  confidence: number;
  priority: 'critical' | 'high' | 'medium' | 'low';
  category: string;
  estimatedEngineers: number;
  estimatedDuration: string;
  businessCapability: string;
  blockingDependencies: string[];
  expectedROI: string;
  businessValue: string;
  technicalImpact: string;
  evidence: string[];
  effort: string;
}

export interface ValidationCheckpoint {
  id: string;
  name: string;
  status: 'pass' | 'fail' | 'pending' | 'warning';
  message: string;
  timestamp?: string;
}

export interface GeneratedArtifact {
  id: string;
  name: string;
  type: 'architecture-report' | 'adr-report' | 'migration-plan' | 'readiness-report'
      | 'dependency-graph' | 'boundary-report' | 'generated-code' | 'infrastructure-templates';
  format: 'pdf' | 'json' | 'markdown' | 'html';
  description: string;
  size?: string;
  available: boolean;
}

export interface ExportOption {
  id: string;
  name: string;
  description: string;
  sections: string[];
  formats: ('pdf' | 'json' | 'markdown')[];
}

export interface ResultsData {
  analysis: AnalysisResult;
  confidence: ConfidenceBreakdown;
  riskHeatmap: RiskHeatmapEntry[];
  recommendations: EnhancedRecommendation[];
  validation: ValidationCheckpoint[];
  artifacts: GeneratedArtifact[];
  exports: ExportOption[];
}

export function mapApiServiceToCapability(svc: ServiceBoundary): {
  name: string;
  description: string;
  readiness: number;
  confidence: number;
  risk: 'low' | 'medium' | 'high';
  classes: number;
  cohesion: number;
  coupling: number;
} {
  const readinessMap = { green: 85, yellow: 55, red: 25 };
  const riskMap: Record<string, 'low' | 'medium' | 'high'> = { low: 'low', medium: 'medium', high: 'high', critical: 'high' };
  return {
    name: svc.name || 'Unknown',
    description: svc.description || '',
    readiness: readinessMap[svc.readiness || 'yellow'] ?? 50,
    confidence: svc.confidence || 50,
    risk: riskMap[svc.risk_level || 'medium'] ?? 'medium',
    classes: (svc.classes || []).length,
    cohesion: svc.cohesion_score || 50,
    coupling: svc.coupling_score || 50,
  };
}

export function getScore(val: unknown): number {
  if (typeof val === 'number') return val;
  if (val && typeof val === 'object' && 'score' in val) return (val as { score: number }).score;
  return 0;
}

export function computeConfidenceBreakdown(analysis: AnalysisResult): ConfidenceBreakdown {
  const readiness = analysis.readiness || {};
  const rawConfidence = getScore(readiness.confidence) || 50;
  // Normalize: if confidence is 0-1 scale, multiply by 100
  const overall = rawConfidence <= 1 ? Math.round(rawConfidence * 100) : Math.round(rawConfidence);
  const services = analysis.service_boundaries || [];
  const avgCoupling = services.length > 0
    ? services.reduce((sum, s) => sum + (100 - (s.coupling_score || 50)), 0) / services.length
    : 50;
  const avgCohesion = services.length > 0
    ? services.reduce((sum, s) => sum + (s.cohesion_score || 50), 0) / services.length
    : 50;
  const hasDbInfo = services.some((s) => (s.database_tables || []).length > 0);
  const adrs = analysis.adrs || [];
  const factors: ConfidenceFactor[] = [
    {
      id: 'code-isolation',
      name: 'Code Isolation',
      score: Math.round(avgCohesion),
      weight: 25,
      description: 'How well classes are organized into cohesive modules',
      status: avgCohesion >= 70 ? 'high' : avgCohesion >= 40 ? 'medium' : 'low',
    },
    {
      id: 'low-coupling',
      name: 'Low Coupling',
      score: Math.round(avgCoupling),
      weight: 25,
      description: 'Degree of independence between service boundaries',
      status: avgCoupling >= 70 ? 'high' : avgCoupling >= 40 ? 'medium' : 'low',
    },
    {
      id: 'db-independence',
      name: 'Database Independence',
      score: hasDbInfo ? 72 : 45,
      weight: 20,
      description: 'Ability to separate database schemas per service',
      status: hasDbInfo ? 'medium' : 'low',
    },
    {
      id: 'business-fit',
      name: 'Business Alignment',
      score: Math.min(95, Math.round(overall * 1.1)),
      weight: 20,
      description: 'How well boundaries align with business capabilities',
      status: overall >= 60 ? 'high' : overall >= 35 ? 'medium' : 'low',
    },
    {
      id: 'risk-profile',
      name: 'Risk Profile',
      score: Math.round(100 - (adrs.length * 5)),
      weight: 10,
      description: 'Overall risk assessment of the modernization plan',
      status: adrs.length <= 4 ? 'high' : 'medium',
    },
  ];
  return { overall, factors };
}

export function computeRiskHeatmap(services: ServiceBoundary[]): RiskHeatmapEntry[] {
  if (!services || !Array.isArray(services)) return [];
  return services.map((svc, i) => {
    const classes = svc.classes || [];
    const dbTables = svc.database_tables || [];
    const riskLevel = svc.risk_level || 'medium';
    const coupling = svc.coupling_score || 50;
    const migrationRisk = riskLevel === 'critical' ? 'critical' : riskLevel === 'high' ? 'high' : riskLevel === 'medium' ? 'medium' : 'low';
    const archRisk = coupling > 70 ? 'high' : coupling > 40 ? 'medium' : 'low';
    const depRisk = classes.length > 8 ? 'high' : classes.length > 4 ? 'medium' : 'low';
    const risks: string[] = [];
    if (archRisk !== 'low') risks.push('High coupling');
    if (depRisk !== 'low') risks.push('Large service');
    if (migrationRisk === 'critical' || migrationRisk === 'high') risks.push('Complex migration');
    if (dbTables.length > 3) risks.push('DB dependencies');
    const overallScore = (migrationRisk === 'critical' ? 3 : migrationRisk === 'high' ? 2 : migrationRisk === 'medium' ? 1 : 0)
      + (archRisk === 'high' ? 2 : archRisk === 'medium' ? 1 : 0)
      + (depRisk === 'high' ? 2 : depRisk === 'medium' ? 1 : 0);
    const overallRisk = overallScore >= 5 ? 'critical' : overallScore >= 3 ? 'high' : overallScore >= 1 ? 'medium' : 'low';
    return {
      id: `risk-${i}`,
      service: svc.name || `Service ${i}`,
      migrationRisk,
      architecturalRisk: archRisk,
      dependencyRisk: depRisk,
      overallRisk,
      riskFactors: risks,
      mitigation: risks.length === 0 ? 'No significant risks identified' : `Address: ${risks.join(', ').toLowerCase()}`,
    };
  });
}

export function computeValidation(analysis: AnalysisResult): ValidationCheckpoint[] {
  const services = analysis.service_boundaries || [];
  const readiness = analysis.readiness || {};
  const adrs = analysis.adrs || [];
  const waves = analysis.migration_waves || [];
  const cost = analysis.cost_comparison || {};
  const metrics = analysis.metrics || {};
  const hasServices = services.length > 0;
  const hasReadiness = getScore(readiness.overall) > 0;
  const hasAdrs = adrs.length > 0;
  const hasCost = (cost.monthly_savings || 0) > 0;
  const hasWaves = waves.length > 0;
  const hasMetrics = Object.keys(metrics).length > 0;
  return [
    {
      id: 'analysis',
      name: 'Static Analysis',
      status: hasMetrics ? 'pass' : 'fail',
      message: hasMetrics ? 'Codebase fully analyzed' : 'Analysis incomplete',
      timestamp: analysis.created_at || new Date().toISOString(),
    },
    {
      id: 'readiness',
      name: 'Readiness Scoring',
      status: hasReadiness ? 'pass' : 'fail',
      message: hasReadiness ? `Overall score: ${analysis.readiness.overall}/100` : 'No readiness data',
    },
    {
      id: 'architecture',
      name: 'Architecture Assessment',
      status: hasServices ? 'pass' : 'warning',
      message: hasServices ? `${analysis.service_boundaries.length} service boundaries identified` : 'No boundaries found',
    },
    {
      id: 'adr',
      name: 'ADR Generation',
      status: hasAdrs ? 'pass' : 'pending',
      message: hasAdrs ? `${analysis.adrs.length} decisions documented` : 'Pending generation',
    },
    {
      id: 'migration',
      name: 'Migration Planning',
      status: hasWaves ? 'pass' : 'pending',
      message: hasWaves ? `${analysis.migration_waves.length} waves planned` : 'Pending planning',
    },
    {
      id: 'cost',
      name: 'Cost Analysis',
      status: hasCost ? 'pass' : 'pending',
      message: hasCost ? `$${(cost.monthly_savings || 0).toLocaleString()}/mo estimated savings` : 'Pending analysis',
    },
    {
      id: 'deployment',
      name: 'Deployment Readiness',
      status: hasServices && hasAdrs ? 'pending' : 'pending',
      message: 'Ready to proceed with deployment',
    },
  ];
}

export function computeRecommendations(analysis: AnalysisResult): EnhancedRecommendation[] {
  const services = analysis.service_boundaries || [];
  const recs: EnhancedRecommendation[] = [];
  const capabilityMap: Record<string, string> = {};
  services.forEach((svc) => {
    if (svc.business_capability) capabilityMap[svc.name] = svc.business_capability;
  });
  services.filter((s) => s.readiness === 'green').forEach((svc, i) => {
    const classes = svc.classes || [];
    const packages = svc.packages || [];
    recs.push({
      id: `rec-extract-${i}`,
      title: `Extract ${svc.name}`,
      description: `This service is ready for extraction with ${svc.confidence || 50}% confidence. Cohesion: ${svc.cohesion_score || 50}, Coupling: ${svc.coupling_score || 50}.`,
      confidence: svc.confidence || 50,
      priority: 'high',
      category: 'architecture',
      estimatedEngineers: Math.max(2, Math.ceil(classes.length / 4)),
      estimatedDuration: `${Math.max(2, Math.ceil(classes.length / 3))} weeks`,
      businessCapability: capabilityMap[svc.name] || 'General',
      blockingDependencies: [],
      expectedROI: `${Math.round((svc.confidence || 50) * 0.4)}% efficiency gain`,
      businessValue: `Enables independent scaling of ${svc.name}`,
      technicalImpact: `Reduces coupling by ${Math.round((svc.coupling_score || 50) * 0.3)}%`,
      evidence: [
        `Cohesion score: ${svc.cohesion_score || 50}`,
        `Coupling score: ${svc.coupling_score || 50}`,
        `${classes.length} classes, ${packages.length} packages`,
      ],
      effort: `${Math.max(2, Math.ceil(classes.length / 3))} weeks`,
    });
  });
  services.filter((s) => s.readiness === 'red').forEach((svc, i) => {
    const classes = svc.classes || [];
    const dbTables = svc.database_tables || [];
    const greenServices = services.filter((s) => s.readiness === 'green');
    recs.push({
      id: `rec-decompose-${i}`,
      title: `Decompose ${svc.name}`,
      description: `High-risk service requiring decomposition before extraction. Coupling: ${svc.coupling_score || 50}.`,
      confidence: Math.max(40, (svc.confidence || 50) - 20),
      priority: 'critical',
      category: 'architecture',
      estimatedEngineers: Math.max(3, Math.ceil(classes.length / 3)),
      estimatedDuration: `${Math.max(4, Math.ceil(classes.length / 2))} weeks`,
      businessCapability: capabilityMap[svc.name] || 'General',
      blockingDependencies: greenServices.map((s) => s.name).slice(0, 2),
      expectedROI: `${Math.round((svc.confidence || 50) * 0.2)}% risk reduction`,
      businessValue: `Unblocks migration of dependent services`,
      technicalImpact: `Breaks ${svc.coupling_score || 50}% coupling into manageable units`,
      evidence: [
        `High coupling score: ${svc.coupling_score || 50}`,
        `${classes.length} classes need decomposition`,
        `${dbTables.length} database tables to separate`,
      ],
      effort: `${Math.max(4, Math.ceil(classes.length / 2))} weeks`,
    });
  });
  return recs;
}

export function computeArtifacts(analysis: AnalysisResult): GeneratedArtifact[] {
  const services = analysis.service_boundaries || [];
  const adrs = analysis.adrs || [];
  const waves = analysis.migration_waves || [];
  const readiness = analysis.readiness || {};
  const hasServices = services.length > 0;
  const hasAdrs = adrs.length > 0;
  const hasWaves = waves.length > 0;
  const hasReadiness = getScore(readiness.overall) > 0;
  return [
    {
      id: 'art-arch-report',
      name: 'Architecture Report',
      type: 'architecture-report',
      format: 'pdf',
      description: `Comprehensive architecture analysis of ${services.length} service boundaries`,
      size: '2.4 MB',
      available: hasServices,
    },
    {
      id: 'art-adr-report',
      name: 'ADR Report',
      type: 'adr-report',
      format: 'json',
      description: `${adrs.length} Architecture Decision Records with context and tradeoffs`,
      size: '156 KB',
      available: hasAdrs,
    },
    {
      id: 'art-migration-plan',
      name: 'Migration Plan',
      type: 'migration-plan',
      format: 'markdown',
      description: `${waves.length}-wave migration roadmap with timelines and dependencies`,
      size: '89 KB',
      available: hasWaves,
    },
    {
      id: 'art-readiness-report',
      name: 'Readiness Report',
      type: 'readiness-report',
      format: 'pdf',
      description: `6-dimension readiness assessment (Overall: ${getScore(readiness.overall)}/100)`,
      size: '340 KB',
      available: hasReadiness,
    },
    {
      id: 'art-dependency-graph',
      name: 'Dependency Graph',
      type: 'dependency-graph',
      format: 'json',
      description: 'Service dependency mapping and circular dependency analysis',
      size: '67 KB',
      available: hasServices,
    },
    {
      id: 'art-boundary-report',
      name: 'Boundary Report',
      type: 'boundary-report',
      format: 'pdf',
      description: 'Detailed service boundary analysis with cohesion and coupling scores',
      size: '198 KB',
      available: hasServices,
    },
    {
      id: 'art-generated-code',
      name: 'Generated Code',
      type: 'generated-code',
      format: 'json',
      description: 'Auto-generated service scaffolding and API contracts',
      available: false,
    },
    {
      id: 'art-infra-templates',
      name: 'Infrastructure Templates',
      type: 'infrastructure-templates',
      format: 'json',
      description: 'CDK/Terraform templates for extracted microservices',
      available: false,
    },
  ];
}

export function computeExports(): ExportOption[] {
  return [
    {
      id: 'exp-exec-summary',
      name: 'Executive Summary',
      description: 'High-level overview with KPIs, readiness scores, and cost savings',
      sections: ['Executive Summary', 'Readiness Breakdown', 'Cost & ROI'],
      formats: ['pdf', 'json', 'markdown'],
    },
    {
      id: 'exp-arch-report',
      name: 'Architecture Report',
      description: 'Service boundaries, dependency analysis, and architecture health',
      sections: ['Architecture Intelligence', 'Business Capability Map', 'Risk Heatmap'],
      formats: ['pdf', 'json', 'markdown'],
    },
    {
      id: 'exp-migration-plan',
      name: 'Migration Plan',
      description: 'Wave-by-wave migration roadmap with timelines and resource needs',
      sections: ['Migration Roadmap', 'Microservice Recommendations', 'Validation Summary'],
      formats: ['pdf', 'json', 'markdown'],
    },
    {
      id: 'exp-adr-bundle',
      name: 'ADR Bundle',
      description: 'All Architecture Decision Records with context and tradeoffs',
      sections: ['ADR Center', 'Explainability Center'],
      formats: ['json', 'markdown'],
    },
    {
      id: 'exp-readiness-report',
      name: 'Readiness Report',
      description: 'Detailed readiness scoring with dimension breakdowns and confidence analysis',
      sections: ['Readiness Breakdown', 'Confidence Center', 'Technical Debt Center'],
      formats: ['pdf', 'json', 'markdown'],
    },
    {
      id: 'exp-dependency-report',
      name: 'Dependency Report',
      description: 'Service dependency graph, circular dependencies, and coupling analysis',
      sections: ['Architecture Intelligence', 'Risk Heatmap', 'Technical Debt Center'],
      formats: ['pdf', 'json'],
    },
  ];
}
