export type JobExtendedStatus =
  | 'queued'
  | 'uploading'
  | 'validating'
  | 'analyzing'
  | 'ai_processing'
  | 'generating_report'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface PipelineStage {
  id: string;
  key: string;
  label: string;
  icon: string;
  order: number;
}

export interface JobDetail {
  id: string;
  projectName: string;
  fileName: string;
  fileSize: number;
  version: string;
  status: JobExtendedStatus;
  currentStage: string;
  progress: number;
  startedAt: string;
  completedAt: string | null;
  elapsed: number;
  estimatedRemaining: number;
  currentTask: string;
  architectureScore: number | null;
  aiConfidence: number | null;
  readinessScore: number | null;
  riskLevel: 'low' | 'medium' | 'high' | null;
  servicesCount: number | null;
  failureReason: string | null;
  failedStage: string | null;
  stagesCompleted: string[];
  metadata: {
    projectName: string;
    version: string;
    description: string;
    businessDomain: string;
    teamName: string;
    owner: string;
  };
}

export interface ActivityEvent {
  id: string;
  jobId: string;
  projectName: string;
  type: 'upload' | 'analysis_start' | 'stage_complete' | 'ai_complete' | 'adr_generated' | 'report_generated' | 'failed';
  message: string;
  timestamp: string;
  stage?: string;
}

export interface JobSummary {
  totalProjects: number;
  queuedJobs: number;
  runningJobs: number;
  completedJobs: number;
  failedJobs: number;
  avgAnalysisTime: number;
  avgConfidence: number;
  successRate: number;
}

export const PIPELINE_STAGES: PipelineStage[] = [
  { id: 'ps1',  key: 'extraction',           label: 'Extraction',           icon: 'Upload',      order: 0 },
  { id: 'ps2',  key: 'static_analysis',      label: 'Static Analysis',      icon: 'Search',      order: 1 },
  { id: 'ps3',  key: 'enterprise_analysis',  label: 'Enterprise Analysis',  icon: 'Building2',   order: 2 },
  { id: 'ps4',  key: 'ai_boundaries',        label: 'Service Boundaries',   icon: 'Layers',      order: 3 },
  { id: 'ps5',  key: 'ai_readiness',         label: 'Readiness Scoring',    icon: 'CheckCircle', order: 4 },
  { id: 'ps6',  key: 'ai_adrs',              label: 'ADR Generation',       icon: 'FileText',    order: 5 },
  { id: 'ps7',  key: 'ai_migration',         label: 'Migration Planning',   icon: 'Route',       order: 6 },
  { id: 'ps8',  key: 'ai_cost',              label: 'Cost Analysis',        icon: 'BarChart3',   order: 7 },
  { id: 'ps9',  key: 'ai_explainability',    label: 'Explainability',       icon: 'Brain',       order: 8 },
  { id: 'ps10', key: 'results_assembly',     label: 'Results Assembly',     icon: 'GitBranch',   order: 9 },
  { id: 'ps11', key: 'report_generation',    label: 'Report Generation',    icon: 'FileText',    order: 10 },
  { id: 'ps12', key: 'manifest',             label: 'Manifest',             icon: 'Trophy',      order: 11 },
];

export const STATUS_CONFIG: Record<JobExtendedStatus, { color: string; bg: string; label: string }> = {
  queued: { color: 'text-gray-600 dark:text-gray-400', bg: 'bg-gray-100 dark:bg-gray-800', label: 'Queued' },
  uploading: { color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-100 dark:bg-blue-900/30', label: 'Uploading' },
  validating: { color: 'text-indigo-600 dark:text-indigo-400', bg: 'bg-indigo-100 dark:bg-indigo-900/30', label: 'Validating' },
  analyzing: { color: 'text-primary', bg: 'bg-primary/10', label: 'Analyzing' },
  ai_processing: { color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-100 dark:bg-purple-900/30', label: 'AI Processing' },
  generating_report: { color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-100 dark:bg-amber-900/30', label: 'Generating Report' },
  paused: { color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-100 dark:bg-amber-900/30', label: 'Paused' },
  completed: { color: 'text-green-600 dark:text-green-400', bg: 'bg-green-100 dark:bg-green-900/30', label: 'Completed' },
  failed: { color: 'text-destructive', bg: 'bg-destructive/10', label: 'Failed' },
  cancelled: { color: 'text-muted-foreground', bg: 'bg-muted', label: 'Cancelled' },
};
