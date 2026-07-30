import axios from 'axios';

const apiKey = import.meta.env.VITE_API_KEY || '';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: apiKey ? { 'X-API-Key': apiKey } : {},
});

export const uploadCodebase = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const startAnalysis = async (jobId: string) => {
  const response = await api.post(`/analyze/${jobId}`);
  return response.data;
};

export const getJobStatus = async (jobId: string) => {
  const response = await api.get(`/results/${jobId}`);
  return response.data;
};

export const getAnalysisResults = async (jobId: string) => {
  const response = await api.get(`/results/${jobId}/analysis`);
  return response.data;
};

export const listJobs = async () => {
  const response = await api.get('/jobs');
  return response.data;
};

export const deployService = async (jobId: string, serviceName: string) => {
  const response = await api.post('/deploy', {
    job_id: jobId,
    service_name: serviceName,
  });
  return response.data;
};

export default api;
