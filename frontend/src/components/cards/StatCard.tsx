import React from 'react';
import { Target, Shield, Brain, Layers, DollarSign, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { KPICard } from '@/types/dashboard';

const iconMap: Record<string, React.ElementType> = {
  Target, Shield, Brain, Layers, DollarSign,
};

const accentColors: Record<string, string> = {
  good: 'border-l-success',
  warning: 'border-l-warning',
  critical: 'border-l-danger',
};

const iconStyles: Record<string, string> = {
  blue: 'bg-info-bg text-info',
  green: 'bg-success-bg text-success',
  yellow: 'bg-warning-bg text-warning',
  red: 'bg-danger-bg text-danger',
  purple: 'bg-[hsl(var(--stage-ai-boundaries)/0.15)] text-[hsl(var(--stage-ai-boundaries))]',
  cyan: 'bg-[hsl(var(--stage-ai-readiness)/0.15)] text-[hsl(var(--stage-ai-readiness))]',
};

const trendIcon = {
  up: TrendingUp,
  down: TrendingDown,
  neutral: Minus,
};

const trendColors = {
  up: 'text-success',
  down: 'text-danger',
  neutral: 'text-muted-foreground',
};

export const StatCard = React.memo(function StatCard({ data }: { data: KPICard }) {
  const Icon = iconMap[data.icon] || Target;
  const TrendIcon = data.trend ? trendIcon[data.trend.direction] : null;

  return (
    <div className={cn(
      'relative overflow-hidden rounded-xl border bg-card p-5 transition-all duration-fast hover:shadow-md',
      'border-l-[3px]',
      accentColors[data.status] || 'border-l-border'
    )}>
      <div className="flex items-start justify-between mb-4">
        <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center shrink-0', iconStyles[data.color])}>
          <Icon className="w-4.5 h-4.5" />
        </div>
        {data.trend && TrendIcon && (
          <div className={cn('flex items-center gap-1.5 text-xs', trendColors[data.trend.direction])}>
            <TrendIcon className="w-3.5 h-3.5" />
            <span className="font-medium">{data.trend.value}{data.trend.label ? ` ${data.trend.label}` : ''}</span>
          </div>
        )}
      </div>
      <div className="text-caption text-muted-foreground mb-0.5">{data.title}</div>
      <div className="flex items-baseline gap-1">
        <span className="text-2xl font-bold text-foreground tracking-tight tabular-nums">
          {typeof data.value === 'number' ? data.value : data.value}
        </span>
        {data.unit && <span className="text-sm font-normal text-muted-foreground">{data.unit}</span>}
      </div>
      {data.description && (
        <p className="text-xs text-muted-foreground/70 mt-1.5 line-clamp-1">{data.description}</p>
      )}
    </div>
  );
});
