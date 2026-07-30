import api from './api';
import type { JobResponse, AnalysisResult, DeployResponse } from '@/types';

export async function uploadCodebase(file: File): Promise<JobResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
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

export async function deleteJob(jobId: string): Promise<{ status: string; job_id: string }> {
  const { data } = await api.delete(`/jobs/${jobId}`);
  return data;
}

export async function deleteAllJobs(): Promise<{ status: string; count: number }> {
  const { data } = await api.delete('/jobs');
  return data;
}

export async function deployService(jobId: string, serviceName: string): Promise<DeployResponse> {
  const { data } = await api.post('/deploy', { job_id: jobId, service_name: serviceName });
  return data;
}
