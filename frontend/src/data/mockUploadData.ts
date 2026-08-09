import type { UploadHistoryEntry, SupportedFramework, WorkflowStep, UploadValidation } from '@/types/upload';

export const mockUploadHistory: UploadHistoryEntry[] = [
  {
    id: 'u1',
    projectName: 'E-Commerce Monolith',
    version: '2.4.1',
    uploadDate: '2026-07-25T14:30:00Z',
    status: 'completed',
    readiness: 34,
    lastAnalysis: '2026-07-25T14:35:00Z',
    fileName: 'ecommerce-monolith.zip',
    fileSize: 45219840,
    jobId: 'job-ecom-001',
  },
  {
    id: 'u2',
    projectName: 'Hospital Management',
    version: '1.8.0',
    uploadDate: '2026-07-24T09:15:00Z',
    status: 'completed',
    readiness: 29,
    lastAnalysis: '2026-07-24T09:22:00Z',
    fileName: 'hospital-monolith.zip',
    fileSize: 38797312,
    jobId: 'job-hosp-002',
  },
  {
    id: 'u3',
    projectName: 'Banking Platform',
    version: '3.1.0',
    uploadDate: '2026-07-20T16:45:00Z',
    status: 'completed',
    readiness: 67,
    lastAnalysis: '2026-07-20T16:52:00Z',
    fileName: 'banking-platform.zip',
    fileSize: 52428800,
    jobId: 'job-bank-003',
  },
  {
    id: 'u4',
    projectName: 'Insurance Core',
    version: '1.2.0',
    uploadDate: '2026-07-18T11:00:00Z',
    status: 'in_progress',
    readiness: null,
    lastAnalysis: null,
    fileName: 'insurance-core.zip',
    fileSize: 29360128,
    jobId: 'job-ins-004',
  },
  {
    id: 'u5',
    projectName: 'CRM System',
    version: '2.0.0',
    uploadDate: '2026-07-15T08:30:00Z',
    status: 'failed',
    readiness: null,
    lastAnalysis: null,
    fileName: 'crm-system.zip',
    fileSize: 15728640,
    jobId: null,
  },
];

export const mockSupportedFrameworks: SupportedFramework[] = [
  { id: 'spring', name: 'Spring Boot', icon: 'Leaf', description: 'Java-based enterprise framework', supported: true, version: '2.x / 3.x' },
  { id: 'java', name: 'Java', icon: 'Coffee', description: 'Core Java applications', supported: true, version: '8+' },
  { id: 'maven', name: 'Maven', icon: 'Package', description: 'Build automation & dependency management', supported: true, version: '3.x' },
  { id: 'gradle', name: 'Gradle', icon: 'Boxes', description: 'Build automation tool', supported: true, version: '7.x+' },
  { id: 'node', name: 'Node.js', icon: 'Server', description: 'JavaScript runtime', supported: false },
  { id: 'dotnet', name: '.NET', icon: 'Braces', description: 'Microsoft framework', supported: false },
  { id: 'python', name: 'Python', icon: 'Code', description: 'Python applications', supported: false },
];

export const mockWorkflowSteps: WorkflowStep[] = [
  { id: 'ws1', step: 1, title: 'Upload', description: 'Upload your ZIP archive', icon: 'Upload', status: 'pending' },
  { id: 'ws2', step: 2, title: 'Static Analysis', description: 'Code quality & complexity metrics', icon: 'Search', status: 'pending' },
  { id: 'ws3', step: 3, title: 'Architecture Intelligence', description: 'Service boundary detection', icon: 'GitBranch', status: 'pending' },
  { id: 'ws4', step: 4, title: 'AI Recommendations', description: 'Migration strategy & priorities', icon: 'Brain', status: 'pending' },
  { id: 'ws5', step: 5, title: 'Executive Report', description: 'Comprehensive assessment report', icon: 'FileText', status: 'pending' },
];

export const defaultValidations: UploadValidation[] = [
  { id: 'v1', label: 'ZIP format verified', description: 'File begins with a valid ZIP header (PK)', status: 'pending', icon: 'FileArchive' },
  { id: 'v2', label: 'File size acceptable', description: 'Archive is within the 500 MB upload limit', status: 'pending', icon: 'HardDrive' },
  { id: 'v3', label: 'File is a .zip archive', description: 'Filename ends with .zip', status: 'pending', icon: 'FileText' },
  { id: 'v4', label: 'Archive is not empty', description: 'File size is greater than zero bytes', status: 'pending', icon: 'Files' },
];
