import React from 'react';
import { AlertOctagon, Zap, Trash2, AlignLeft, GitMerge, BarChart } from 'lucide-react';
import { cn } from '@/utils/cn';
import { TrendIndicator } from '@/components/ui/StatusBadge';
import type { DebtItem } from '@/types/dashboard';

const iconMap: Record<string, React.ElementType> = {
  AlertOctagon, Zap, Trash2, AlignLeft, GitMerge, BarChart,
};

const severityColors = {
  critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  low: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
};

export const DebtCard = React.memo(function DebtCard({ data }: { data: DebtItem }) {
  const Icon = iconMap[data.icon] || AlertOctagon;
  return (
    <article className="bg-card rounded-xl border p-5 hover:shadow-md transition-all">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="w-5 h-5 text-muted-foreground" />
          <h3 className="font-medium text-foreground text-sm">{data.category}</h3>
        </div>
        <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', severityColors[data.severity])}>
          {data.severity.toUpperCase()}
        </span>
      </div>
      <div className="text-3xl font-bold text-foreground mb-1">{data.count}</div>
      {data.trend && (
        <TrendIndicator value={data.trend.value} direction={data.trend.direction} className="mb-2" />
      )}
      <p className="text-xs text-muted-foreground">{data.recommendation}</p>
    </article>
  );
});
