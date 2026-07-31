export interface KPICard {
  id: string;
  title: string;
  value: number | string;
  unit?: string;
  description: string;
  trend?: {
    value: number;
    label: string;
    direction: 'up' | 'down' | 'neutral';
  };
  icon: string;
  color: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'cyan';
  status: 'good' | 'warning' | 'critical';
}

export interface ReadinessDimension {
  id: string;
  name: string;
  score: number;
  weight: number;
  evidence: string;
  evidence_bullets?: string[];
  status: 'healthy' | 'warning' | 'critical';
  icon: string;
}

export interface ReadinessBreakdown {
  overall: number;
  confidence: number;
  dimensions: ReadinessDimension[];
}

export interface ConfidenceFactor {
  id: string;
  name: string;
  score: number;
  weight: number;
  description: string;
}

export interface ConfidenceBreakdown {
  overall: number;
  factors: ConfidenceFactor[];
}

export interface BusinessCapability {
  id: string;
  name: string;
  description: string;
  readiness: number;
  confidence: number;
  risk: 'low' | 'medium' | 'high';
  classes: number;
  recommendedService: string;
  color: string;
  icon: string;
}

export interface HealthMetric {
  id: string;
  title: string;
  value: number;
  maxValue: number;
  unit: string;
  status: 'healthy' | 'warning' | 'critical';
  description: string;
  icon: string;
}

export interface ServiceReadiness {
  id: string;
  name: string;
  readiness: 'green' | 'yellow' | 'red';
  risk: 'low' | 'medium' | 'high';
  confidence: number;
  cohesion: number;
  coupling: number;
  classes: number;
  status: 'ready' | 'needs_work' | 'not_ready';
}

export interface MigrationTimelineWave {
  id: string;
  wave: number;
  name: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  duration: string;
  durationWeeks: { start: number; end: number };
  services: string[];
  risk: 'low' | 'medium' | 'high' | 'critical';
  status: 'completed' | 'in_progress' | 'planned' | 'blocked';
  progress: number;
  dependencies: string[];
  estimatedEngineers: number;
  estimatedCost: number;
}

export interface AIRecommendation {
  id: string;
  title: string;
  recommendation: string;
  businessValue: string;
  technicalImpact: string;
  confidence: number;
  evidence: string[];
  priority: 'critical' | 'high' | 'medium' | 'low';
  category: 'architecture' | 'performance' | 'security' | 'cost' | 'reliability';
  effort: string;
  impact: 'high' | 'medium' | 'low';
}

export interface ExplainabilityEntry {
  id: string;
  service: string;
  primaryReason: string;
  secondaryReasons: string[];
  evidence: {
    codeIsolation: string;
    lowCoupling: string;
    databaseIndependence: string;
    businessAlignment: string;
  };
  tradeoffs: {
    pros: string[];
    cons: string[];
  };
  alternatives: string[];
  impact: {
    business: string;
    technical: string;
    risk: string;
  };
  confidence: number;
  confidenceFactors: ConfidenceFactor[];
}

export interface ADRPreview {
  id: string;
  title: string;
  status: 'proposed' | 'accepted' | 'deprecated' | 'superseded';
  context: string;
  decision: string;
  consequences: {
    positive: string[];
    negative: string[];
    risks: string[];
  };
  alternatives: string[];
  confidence: number;
  service: string;
}

export interface DebtItem {
  id: string;
  category: string;
  count: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  recommendation: string;
  description: string;
  icon: string;
  trend?: {
    value: number;
    direction: 'up' | 'down' | 'neutral';
  };
}

export interface CostBreakdownData {
  current: {
    monthly: number;
    breakdown: {
      compute: number;
      storage: number;
      networking: number;
      operations: number;
      licensing: number;
    };
  };
  projected: {
    monthly: number;
    breakdown: {
      compute: number;
      storage: number;
      networking: number;
      operations: number;
      licensing: number;
    };
  };
  savings: {
    monthly: number;
    annual: number;
    percentage: number;
  };
  roi: {
    paybackPeriod: string;
    breakEvenMonths: number;
    totalSavings3Year: number;
  };
}

export interface ChartDataPoint {
  name: string;
  current: number;
  projected: number;
  savings?: number;
}

export interface RecentAnalysis {
  id: string;
  projectName: string;
  date: string;
  status: 'completed' | 'in_progress' | 'failed';
  readiness: number;
  risk: 'low' | 'medium' | 'high';
  services: number;
  fileName: string;
}

export interface QuickAction {
  id: string;
  title: string;
  description: string;
  icon: string;
  href: string;
  color: 'blue' | 'green' | 'purple' | 'orange';
}
