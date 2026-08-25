import React from 'react';
import { Loader2, CheckCircle, XCircle, Upload, Clock, Ban, AlertCircle, FileText, Brain, Pause } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { JobExtendedStatus } from '@/types/jobs';
import { STATUS_CONFIG } from '@/types/jobs';

const statusIcons: Record<JobExtendedStatus, React.ElementType> = {
  queued: Clock,
  uploading: Upload,
  validating: AlertCircle,
  analyzing: Loader2,
  ai_processing: Brain,
  generating_report: FileText,
  paused: Pause,
  completed: CheckCircle,
  failed: XCircle,
  cancelled: Ban,
};

interface StageBadgeProps {
  status: JobExtendedStatus;
  size?: 'sm' | 'md';
}

export function StageBadge({ status, size = 'sm' }: StageBadgeProps) {
  const config = STATUS_CONFIG[status];
  const Icon = statusIcons[status];
  const isAnimating = status === 'analyzing' || status === 'ai_processing' || status === 'generating_report' || status === 'uploading' || status === 'validating';

  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 rounded-full font-medium shrink-0',
      config.bg, config.color,
      size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'
    )}>
      <Icon className={cn(size === 'sm' ? 'w-3 h-3' : 'w-4 h-4', isAnimating && 'animate-spin')} />
      {config.label}
    </span>
  );
}
