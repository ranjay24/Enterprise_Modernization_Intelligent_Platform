import { Loader2, CheckCircle, XCircle, Upload } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { JobStatus } from '@/types';

const config: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  uploaded: { icon: Upload, color: 'text-muted-foreground bg-muted', label: 'Uploaded' },
  analyzing: { icon: Loader2, color: 'text-primary bg-primary/10', label: 'Analyzing' },
  analysis_complete: { icon: CheckCircle, color: 'text-green-600 bg-green-100 dark:bg-green-900/30', label: 'Complete' },
  failed: { icon: XCircle, color: 'text-destructive bg-destructive/10', label: 'Failed' },
  deployed: { icon: CheckCircle, color: 'text-green-600 bg-green-100 dark:bg-green-900/30', label: 'Deployed' },
};

export function JobStatusBadge({ status }: { status: string }) {
  const c = config[status] || config.uploaded;
  const Icon = c.icon;
  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium shrink-0', c.color)}>
      <Icon className={cn('w-3 h-3', status === 'analyzing' && 'animate-spin')} />
      {c.label}
    </span>
  );
}
