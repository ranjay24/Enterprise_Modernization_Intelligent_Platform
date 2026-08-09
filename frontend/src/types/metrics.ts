export interface GodClassMetric {
  name: string;
  package: string;
  lines_of_code: number;
  method_count: number;
  injected_dependencies: number;
  reason?: string;
}

export interface CircularDependencyMetric {
  type?: string;
  cycle: string[];
}

export interface DeadCodeMetric {
  name: string;
  package: string;
  reason: string;
}

export interface ExplainabilityRecommendation {
  service: string;
  primary_reason?: string;
  secondary_reasons?: string[];
  migration_complexity?: string;
  confidence?: number;
}

export interface ExplainabilityData {
  recommendations?: ExplainabilityRecommendation[];
  business_capabilities?: string[];
}
