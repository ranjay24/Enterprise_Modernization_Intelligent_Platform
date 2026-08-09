import api from './api';
import type { JobResponse, AnalysisResult, CodeGenStatus, ArchitectureDesign, CodeGenPlan, CodeGenCodeResponse, ReviewReport } from '@/types';

export async function uploadCodebase(
  file: File,
  onProgress?: (loaded: number, total: number) => void
): Promise<JobResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/upload', formData, {
    onUploadProgress: (e) => {
      const total = e.total && e.total > 0 ? e.total : file.size;
      if (total > 0) onProgress?.(e.loaded, total);
    },
  });
  return data;
}

export async function startAnalysis(jobId: string): Promise<JobResponse> {
  const { data } = await api.post(`/analyze/${jobId}`);
  return data;
}

export async function getJobStatus(jobId: string): Promise<JobResponse> {
  const { data } = await api.get(`/results/${jobId}`);
  return data;
}

export async function getAnalysisResults(jobId: string): Promise<AnalysisResult> {
  const { data } = await api.get(`/results/${jobId}/analysis`);
  return data;
}

export async function listJobs(): Promise<{ jobs: JobResponse[] }> {
  const { data } = await api.get('/jobs');
  return data;
}

export async function pauseJob(jobId: string): Promise<JobResponse> {
  const { data } = await api.post(`/jobs/${jobId}/pause`);
  return data;
}

export async function resumeJob(jobId: string): Promise<JobResponse> {
  const { data } = await api.post(`/jobs/${jobId}/resume`);
  return data;
}

export async function cancelJob(jobId: string): Promise<JobResponse> {
  const { data } = await api.post(`/jobs/${jobId}/cancel`);
  return data;
}

export async function deleteAllJobs(): Promise<{ status: string; count: number }> {
  const { data } = await api.delete('/jobs');
  return data;
}

export async function startCodeGeneration(jobId: string): Promise<{ status: string; job_id: string }> {
  const { data } = await api.post(`/codegen/${jobId}/start`);
  return data;
}

export async function getCodeGenStatus(jobId: string): Promise<CodeGenStatus> {
  const { data } = await api.get(`/codegen/${jobId}/status`);
  return data;
}

export async function getCodeGenArchitecture(jobId: string): Promise<ArchitectureDesign> {
  const { data } = await api.get(`/codegen/${jobId}/architecture`);
  return data;
}

export async function getCodeGenPlan(jobId: string): Promise<CodeGenPlan> {
  const { data } = await api.get(`/codegen/${jobId}/plan`);
  return data;
}

export async function getCodeGenCode(jobId: string, service?: string): Promise<CodeGenCodeResponse> {
  const params = service ? { service } : undefined;
  const { data } = await api.get(`/codegen/${jobId}/code`, { params });
  return data;
}

export async function getCodeGenReview(jobId: string): Promise<ReviewReport> {
  const { data } = await api.get(`/codegen/${jobId}/review`);
  return data;
}
