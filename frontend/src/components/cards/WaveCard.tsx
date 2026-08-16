import React from 'react';
import { Clock, Users } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Badge } from '@/components/ui/Badge';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import type { MigrationTimelineWave } from '@/types/dashboard';

const priorityColors = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-yellow-500',
  low: 'bg-blue-500',
};

const riskBadge = {
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

export const WaveCard = React.memo(function WaveCard({ data }: { data: MigrationTimelineWave }) {
  return (
    <article className="bg-card rounded-xl border p-5 hover:shadow-md transition-all">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold', priorityColors[data.priority])}>
            {data.wave}
          </div>
          <div>
            <h3 className="font-semibold text-foreground text-sm">{data.name}</h3>
            <p className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="w-3 h-3" /> {data.duration}
            </p>
          </div>
        </div>
        <StatusBadge status={data.status} />
      </div>
      {data.status === 'in_progress' && (
        <div className="mb-3">
          <ProgressBar value={data.progress} />
          <p className="text-xs text-muted-foreground mt-1">{data.progress}% complete</p>
        </div>
      )}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {data.services.map((svc) => (
          <Badge key={svc} variant="secondary" className="text-xs">{svc}</Badge>
        ))}
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className={cn('font-medium px-2 py-0.5 rounded-full', riskBadge[data.risk])}>
          {data.risk.toUpperCase()} RISK
        </span>
        <span className="flex items-center gap-1">
          <Users className="w-3 h-3" /> {data.estimatedEngineers} engineers
        </span>
      </div>
      {data.dependencies.length > 0 && (
        <p className="text-xs text-muted-foreground mt-2">
          Depends on: Wave {data.dependencies.map(d => String(d).replace('w', '')).join(', ')}
        </p>
      )}
    </article>
  );
});
