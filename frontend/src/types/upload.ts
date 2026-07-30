export interface ProjectMetadata {
  projectName: string;
  version: string;
  description: string;
  businessDomain: string;
  teamName: string;
  owner: string;
  tags: string[];
  environment: 'development' | 'testing' | 'production';
}

export interface UploadValidation {
  id: string;
  label: string;
  description: string;
  status: 'pending' | 'pass' | 'fail' | 'warning';
  icon: string;
}

export interface UploadProgressData {
  stage: 'idle' | 'uploading' | 'processing' | 'complete' | 'error';
  progress: number;
  uploadedBytes: number;
  totalBytes: number;
  speed: number;
  estimatedRemaining: number;
  fileName: string;
  jobId: string | null;
  error: string | null;
}

export interface UploadHistoryEntry {
  id: string;
  projectName: string;
  version: string;
  uploadDate: string;
  status: 'completed' | 'in_progress' | 'failed' | 'pending';
  readiness: number | null;
  lastAnalysis: string | null;
  fileName: string;
  fileSize: number;
  jobId: string | null;
}

export interface SupportedFramework {
  id: string;
  name: string;
  icon: string;
  description: string;
  supported: boolean;
  version?: string;
}

export interface WorkflowStep {
  id: string;
  step: number;
  title: string;
  description: string;
  icon: string;
  status: 'pending' | 'active' | 'completed';
}

export interface UploadSuccessData {
  projectName: string;
  fileSize: number;
  jobId: string;
  uploadTime: number;
}
