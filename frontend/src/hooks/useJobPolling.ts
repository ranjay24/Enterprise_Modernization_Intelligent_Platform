import { useQuery } from '@tanstack/react-query';
import { getJobStatus } from '@/services/jobService';
import { POLL_INTERVAL_MS, STALE_TIME_MS } from '@/utils/constants';

const TERMINAL_STATUSES = new Set([
  'analysis_complete',
  'generation_complete',
  'generation_with_warnings',
  'generating',
  'paused',
  'cancelled',
  'failed',
  'deployed',
]);

export function useJobPolling(jobId: string | undefined) {
  return useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && TERMINAL_STATUSES.has(status)) return false;
      return POLL_INTERVAL_MS;
    },
    staleTime: STALE_TIME_MS,
  });
}
