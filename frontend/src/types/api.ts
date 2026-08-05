export type JobStatus =
  | 'uploaded'
  | 'analyzing'
  | 'paused'
  | 'cancelled'
  | 'analysis_complete'
  | 'generating'
  | 'generation_complete'
  | 'generation_with_warnings'
  | 'failed'
  | 'deployed';

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  filename: string;
  file_size?: number;
  created_at: string;
  updated_at: string;
  progress: number;
  current_phase: string | null;
  error: string | null;
  completed_phases?: string[];
}

export interface ServiceBoundary {
  name: string;
  description: string;
  cohesion_score: number;
  coupling_score: number;
  classes: string[];
  packages: string[];
  api_endpoints: { method: string; path: string; handler_class: string; handler_method: string }[];
  database_tables: string[];
  confidence: number;
  readiness: 'green' | 'yellow' | 'red';
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  business_capability?: string;
}

export interface ReadinessScores {
  code_quality: number | { score: number; evidence: string };
  architecture: number | { score: number; evidence: string };
  cloud_readiness: number | { score: number; evidence: string };
  service_separation: number | { score: number; evidence: string };
  database_coupling: number | { score: number; evidence: string };
  documentation: number | { score: number; evidence: string };
  overall: number;
  confidence: number;
  summary?: string;
}

export interface ADR {
  id: string;
  title: string;
  status: string;
  context: string;
  decision: string;
  alternatives: string[];
  tradeoffs: { pros: string[]; cons: string[] };
  consequences: { positive: string[]; negative: string[]; risks: string[] };
  confidence: number;
  migration_impact?: {
    complexity: string;
    estimated_effort: string;
    team_size: number;
    risk_factors: string[];
  };
}

export interface MigrationWave {
  wave_number: number;
  name: string;
  services: string[];
  timeline_weeks: number;
  estimated_engineers: number;
  dependencies: string[];
  risk_level: string;
  migration_complexity?: string;
}

export interface CostComparison {
  current_monthly: number;
  post_migration_monthly: number;
  monthly_savings: number;
  annual_savings: number;
  one_time_cost: number;
  payback_months: number;
  breakdown_current: Record<string, number>;
  breakdown_post: Record<string, number>;
  migration_impact?: {
    total_services: number;
    total_waves: number;
    estimated_timeline_weeks: number;
    total_engineers_needed: number;
    risk_summary: string;
  };
}

export interface AnalysisResult {
  job_id: string;
  metrics: Record<string, unknown>;
  service_boundaries: ServiceBoundary[];
  readiness: ReadinessScores;
  adrs: ADR[];
  migration_waves: MigrationWave[];
  cost_comparison: CostComparison;
  explainability: Record<string, unknown>;
  created_at: string;
}

export interface DeployResponse {
  deployment_id: string;
  status: string;
  service_name: string;
  ecs_cluster: string | null;
  ecs_service: string | null;
  alb_dns: string | null;
  health_check_url: string | null;
}
