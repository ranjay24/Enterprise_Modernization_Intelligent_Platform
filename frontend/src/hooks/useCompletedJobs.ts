import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listJobs, getAnalysisResults } from '@/services/jobService';
import type { JobResponse } from '@/types';

const COMPLETED_STATUSES = ['analysis_complete', 'generation_complete', 'generation_with_warnings'];

export function useCompletedJobs() {
  const { data: jobsData, isLoading: jobsLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: listJobs,
    staleTime: 30000,
  });

  const completedJobs: JobResponse[] = (jobsData?.jobs || [])
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
    enabled: !!effectiveJobId,
    staleTime: 60000,
  });

  return {
    completedJobs,
    selectedJobId: effectiveJobId,
    setSelectedJobId,
    selectedJob,
    results,
    isLoading: jobsLoading || resultsLoading,
  };
}
