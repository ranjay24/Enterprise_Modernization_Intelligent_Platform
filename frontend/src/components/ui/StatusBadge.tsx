import { cn } from '@/utils/cn';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface ConfidenceBadgeProps {
  value: number;
  className?: string;
}

export function ConfidenceBadge({ value, className }: ConfidenceBadgeProps) {
  const color = value >= 80 ? 'bg-success-bg text-success'
    : value >= 60 ? 'bg-warning-bg text-warning'
    : 'bg-danger-bg text-danger';

  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded text-xs font-bold tabular-nums', color, className)}>
      {value}%
    </span>
  );
}

interface StatusBadgeProps {
  status: string;
  className?: string;
}

const statusColors: Record<string, string> = {
  healthy: 'bg-success-bg text-success',
  good: 'bg-success-bg text-success',
  completed: 'bg-success-bg text-success',
  ready: 'bg-success-bg text-success',
  warning: 'bg-warning-bg text-warning',
  in_progress: 'bg-info-bg text-info',
  paused: 'bg-warning-bg text-warning',
  cancelled: 'bg-muted text-muted-foreground',
  needs_work: 'bg-warning-bg text-warning',
  critical: 'bg-danger-bg text-danger',
  failed: 'bg-danger-bg text-danger',
  blocked: 'bg-danger-bg text-danger',
  not_ready: 'bg-danger-bg text-danger',
  proposed: 'bg-info-bg text-info',
  accepted: 'bg-success-bg text-success',
  deprecated: 'bg-muted text-muted-foreground',
  planned: 'bg-info-bg text-info',
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span className={cn(
      'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold',
      statusColors[status] || 'bg-muted text-muted-foreground',
      className
    )}>
      {String(status || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
    </span>
  );
}

interface TrendIndicatorProps {
  value: number;
  direction: 'up' | 'down' | 'neutral';
  label?: string;
  className?: string;
}

export function TrendIndicator({ value, direction, label, className }: TrendIndicatorProps) {
  if (direction === 'neutral') {
    return (
      <span className={cn('inline-flex items-center gap-0.5 text-xs text-muted-foreground', className)}>
        <Minus className="w-3 h-3" /> {label}
      </span>
    );
  }

  const Icon = direction === 'up' ? TrendingUp : TrendingDown;
  const color = direction === 'up' ? 'text-success' : 'text-danger';

  return (
    <span className={cn('inline-flex items-center gap-0.5 text-xs', color, className)}>
      <Icon className="w-3 h-3" />
      {value > 0 && `${value}%`}
      {label && <span className="text-muted-foreground ml-1">{label}</span>}
    </span>
  );
}
