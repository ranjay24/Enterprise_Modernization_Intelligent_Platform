import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listJobs } from '@/services/jobService';
import { useAppStore } from '@/store/useAppStore';
import type { JobResponse, JobStatus } from '@/types';

export interface AppNotification {
  id: string;
  jobId: string;
  filename: string;
  title: string;
  status: JobStatus;
  at: number;
  demo?: boolean;
}

const POLL_MS = 20000;
const MAX_NOTIFICATIONS = 12;
const TOAST_MS = 6000;

const TERMINAL_STATUSES: JobStatus[] = [
  'analysis_complete',
  'generation_complete',
  'generation_with_warnings',
  'failed',
];

const NOTEWORTHY_START: JobStatus[] = ['analyzing', 'generating'];

function titleFor(status: JobStatus, filename: string): string {
  switch (status) {
    case 'analysis_complete':
      return `Analysis complete — ${filename}`;
    case 'generation_complete':
      return `Code generation complete — ${filename}`;
    case 'generation_with_warnings':
      return `Code generation finished with warnings — ${filename}`;
    case 'failed':
      return `Analysis failed — ${filename}`;
    case 'analyzing':
      return `Analysis started — ${filename}`;
    case 'generating':
      return `Code generation started — ${filename}`;
    default:
      return `${filename} → ${status}`;
  }
}

function isNoteworthy(from: JobStatus, to: JobStatus): boolean {
  return TERMINAL_STATUSES.includes(to) || (NOTEWORTHY_START.includes(to) && from === 'uploaded');
}

const DEMO_NOTIFICATIONS: AppNotification[] = [
  {
    id: 'demo-1',
    jobId: 'job-bank-003',
    filename: 'banking-core.zip',
    title: 'Analysis complete — banking-core.zip',
    status: 'analysis_complete',
    at: Date.now() - 1000 * 60 * 90,
    demo: true,
  },
  {
    id: 'demo-2',
    jobId: 'job-ecom-001',
    filename: 'ecommerce-platform.zip',
    title: 'Analysis started — ecommerce-platform.zip',
    status: 'analyzing',
    at: Date.now() - 1000 * 60 * 20,
    demo: true,
  },
];

export function useNotifications() {
  const demoMode = useAppStore((s) => s.demoMode);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unseenCount, setUnseenCount] = useState(0);
  const [toast, setToast] = useState<AppNotification | null>(null);
  const previous = useRef<Record<string, JobStatus>>({});
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data } = useQuery({
    queryKey: ['notifications-jobs'],
    queryFn: listJobs,
    enabled: !demoMode,
    refetchInterval: POLL_MS,
    retry: 1,
    staleTime: 5000,
  });

  useEffect(() => {
    if (demoMode) {
      setNotifications(DEMO_NOTIFICATIONS);
      setUnseenCount(DEMO_NOTIFICATIONS.length);
      return;
    }

    const jobs: JobResponse[] = data?.jobs ?? [];
    const prev = previous.current;
    const seen: Record<string, JobStatus> = {};
    const fresh: AppNotification[] = [];
    let newToast: AppNotification | null = null;

    for (const job of jobs) {
      seen[job.job_id] = job.status;
      const before = prev[job.job_id];
      if (!before || before === job.status) continue;
      if (!isNoteworthy(before, job.status)) continue;

      const n: AppNotification = {
        id: `${job.job_id}-${job.status}-${Date.now()}`,
        jobId: job.job_id,
        filename: job.filename,
        title: titleFor(job.status, job.filename),
        status: job.status,
        at: Date.now(),
      };
      fresh.push(n);
      if (TERMINAL_STATUSES.includes(job.status)) newToast = n;
    }

    previous.current = seen;

    if (fresh.length > 0) {
      setNotifications((current) =>
        [...fresh.reverse(), ...current.filter((n) => !n.demo)].slice(0, MAX_NOTIFICATIONS)
      );
      setUnseenCount((count) => count + fresh.length);

      if (newToast) {
        setToast(newToast);
        if (toastTimer.current) clearTimeout(toastTimer.current);
        toastTimer.current = setTimeout(() => setToast(null), TOAST_MS);
      }
    }
  }, [data, demoMode]);

  const markSeen = useCallback(() => {
    setUnseenCount(0);
  }, []);

  const dismissToast = useCallback(() => {
    setToast(null);
    if (toastTimer.current) clearTimeout(toastTimer.current);
  }, []);

  useEffect(() => {
    return () => {
      if (toastTimer.current) clearTimeout(toastTimer.current);
    };
  }, []);

  return { notifications, unseen: unseenCount, toast, markSeen, dismissToast, demoMode };
}
