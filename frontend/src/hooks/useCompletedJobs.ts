import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listJobs, getAnalysisResults } from '@/services/jobService';
import { useAppStore } from '@/store/useAppStore';
import { mockAnalysisResult } from '@/data/mockResults';
import type { JobResponse } from '@/types';

const COMPLETED_STATUSES = ['analysis_complete', 'generation_complete', 'generation_with_warnings'];

const demoJob: JobResponse = {
  job_id: mockAnalysisResult.job_id,
  status: 'analysis_complete',
  filename: 'demo-ecommerce-app.zip',
  file_size: 0,
  created_at: mockAnalysisResult.created_at,
  updated_at: mockAnalysisResult.created_at,
  progress: 100,
  current_phase: null,
  error: null,
};

export function useCompletedJobs() {
  const demoMode = useAppStore((s) => s.demoMode);

  const { data: jobsData, isLoading: jobsLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: listJobs,
    staleTime: 30000,
    enabled: !demoMode,
  });

  const completedJobs: JobResponse[] = demoMode
    ? [demoJob]
    : (jobsData?.jobs || [])
        .filter((j) => COMPLETED_STATUSES.includes(j.status))
        .sort((a, b) => b.created_at.localeCompare(a.created_at));

  const [selectedJobId, setSelectedJobId] = useState<string | undefined>(undefined);

  const effectiveJobId = completedJobs.some((j) => j.job_id === selectedJobId)
    ? selectedJobId
    : completedJobs[0]?.job_id;

  const selectedJob = completedJobs.find((j) => j.job_id === effectiveJobId) || null;

  const { data: results, isLoading: resultsLoading } = useQuery({
    queryKey: ['analysis', effectiveJobId],
    queryFn: () => getAnalysisResults(effectiveJobId!),
    enabled: !!effectiveJobId && !demoMode,
    staleTime: 60000,
  });

  return {
    completedJobs,
    selectedJobId: effectiveJobId,
    setSelectedJobId,
    selectedJob,
    results: demoMode ? mockAnalysisResult : results,
    isLoading: demoMode ? false : jobsLoading || resultsLoading,
    demoMode,
  };
}
