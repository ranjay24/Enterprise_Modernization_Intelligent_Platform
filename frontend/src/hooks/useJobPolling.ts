import { useQuery } from '@tanstack/react-query';
import { getJobStatus } from '@/services/jobService';
import { POLL_INTERVAL_MS, STALE_TIME_MS } from '@/utils/constants';

export function useJobPolling(jobId: string | undefined) {
  return useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'analysis_complete' || status === 'failed') return false;
      return POLL_INTERVAL_MS;
    },
    staleTime: STALE_TIME_MS,
  });
}
