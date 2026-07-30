import { useQuery } from '@tanstack/react-query';
import { getAnalysisResults } from '@/services/jobService';
import { STALE_TIME_MS } from '@/utils/constants';

export function useAnalysisResults(jobId: string | undefined) {
  return useQuery({
    queryKey: ['analysis', jobId],
    queryFn: () => getAnalysisResults(jobId!),
    enabled: !!jobId,
    staleTime: STALE_TIME_MS,
    refetchOnWindowFocus: false,
  });
}
