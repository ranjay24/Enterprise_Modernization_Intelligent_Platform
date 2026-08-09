export const API_BASE = import.meta.env.VITE_API_BASE || '/api';
export const POLL_INTERVAL_MS = 1500;
export const STALE_TIME_MS = 30000;
export const APP_VERSION = '1.0.0';

export const PHASE_LABELS: Record<string, string> = {
  extraction: 'Extracting source code',
  static_analysis: 'Running static analysis',
  enterprise_analysis: 'Analyzing enterprise architecture',
  ai_boundaries: 'Detecting service boundaries',
  ai_readiness: 'Scoring modernization readiness',
  ai_adrs: 'Generating Architecture Decision Records',
  ai_migration: 'Planning migration waves',
  ai_cost: 'Estimating cloud costs',
  ai_explainability: 'Building explainability reports',
  results_assembly: 'Assembling analysis results',
  report_generation: 'Generating final reports',
  manifest: 'Finalizing manifest',
};

export const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  uploaded: { color: 'text-muted-foreground', label: 'Uploaded' },
  analyzing: { color: 'text-primary', label: 'Analyzing' },
  analysis_complete: { color: 'text-green-600', label: 'Complete' },
  failed: { color: 'text-destructive', label: 'Failed' },
  deployed: { color: 'text-green-600', label: 'Deployed' },
};
