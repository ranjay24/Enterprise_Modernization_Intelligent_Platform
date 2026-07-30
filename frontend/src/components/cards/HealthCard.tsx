import React from 'react';
import { Puzzle, Link, Layout, Wrench, AlertTriangle, Activity } from 'lucide-react';
import { cn } from '@/utils/cn';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { StatusBadge } from '@/components/ui/StatusBadge';
import type { HealthMetric } from '@/types/dashboard';

const iconMap: Record<string, React.ElementType> = {
  Puzzle, Link, Layout, Wrench, AlertTriangle, Activity,
};

export const HealthCard = React.memo(function HealthCard({ data }: { data: HealthMetric }) {
  const Icon = iconMap[data.icon] || Activity;
  return (
    <article className="bg-card rounded-xl border p-5 hover:shadow-md transition-all">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="w-5 h-5 text-muted-foreground" />
          <h3 className="font-medium text-foreground text-sm">{data.title}</h3>
        </div>
        <StatusBadge status={data.status} />
      </div>
      <div className="text-2xl font-bold text-foreground mb-1">
        {data.value}<span className="text-sm font-normal text-muted-foreground">{data.unit}</span>
      </div>
      <ProgressBar value={data.value} max={data.maxValue} />
      <p className="text-xs text-muted-foreground mt-2">{data.description}</p>
    </article>
  );
});
