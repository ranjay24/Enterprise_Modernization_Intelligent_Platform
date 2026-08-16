import type { MigrationTimelineWave } from '@/types/dashboard';
import { MigrationTimelineChart } from '@/components/charts/MigrationTimelineChart';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/utils/cn';
import { Users, DollarSign } from 'lucide-react';

function WaveCard({ wave }: { wave: MigrationTimelineWave }) {
  return (
    <div className={cn(
      'rounded-xl border bg-card p-4 transition-all duration-fast hover:shadow-sm',
      wave.status === 'completed' && 'border-l-[3px] border-l-success',
      wave.status === 'in_progress' && 'border-l-[3px] border-l-warning',
      wave.status === 'planned' && 'border-l-[3px] border-l-info',
    )}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={cn(
            'w-6 h-6 rounded flex items-center justify-center text-[11px] font-bold',
            wave.priority === 'critical' ? 'bg-danger-bg text-danger' :
            wave.priority === 'high' ? 'bg-warning-bg text-warning' :
            'bg-info-bg text-info'
          )}>
            {wave.wave}
          </span>
          <h4 className="text-sm font-semibold text-foreground">{wave.name}</h4>
        </div>
        <Badge variant={
          wave.status === 'completed' ? 'success' :
          wave.status === 'in_progress' ? 'warning' : 'outline'
        } size="sm">{wave.status.replace(/_/g, ' ')}</Badge>
      </div>

      <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground flex-wrap">
        <span>{wave.duration}</span>
        <span className="text-border">|</span>
        <span className="flex items-center gap-1">
          <Users className="w-3 h-3" />
          {wave.estimatedEngineers} eng
        </span>
        <span className="text-border">|</span>
        <span className="flex items-center gap-1">
          <DollarSign className="w-3 h-3" />
          ${(wave.estimatedCost / 1000).toFixed(0)}k
        </span>
        <span className="text-border">|</span>
        <span className={cn(
          'font-medium',
          wave.risk === 'low' ? 'text-success' :
          wave.risk === 'medium' ? 'text-warning' : 'text-danger'
        )}>
          {wave.risk} risk
        </span>
      </div>

      {wave.progress > 0 && (
        <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden mb-2">
          <div className={cn(
            'h-full rounded-full transition-all duration-700',
            wave.status === 'completed' ? 'bg-success' : 'bg-primary'
          )} style={{ width: `${wave.progress}%` }} />
        </div>
      )}

      <div className="flex flex-wrap gap-1">
        {wave.services.map((svc) => (
          <span key={svc} className="px-2 py-0.5 rounded bg-muted text-[10px] text-muted-foreground">{svc}</span>
        ))}
      </div>

      {wave.dependencies.length > 0 && (
        <div className="flex items-center gap-1 mt-2 text-[10px] text-muted-foreground">
          <span>Depends on:</span>
          {wave.dependencies.map((dep) => (
            <span key={dep} className="px-1.5 py-0.5 rounded bg-muted">{dep}</span>
          ))}
        </div>
      )}
    </div>
  );
}

export function MigrationTimeline({ waves }: { waves: MigrationTimelineWave[] }) {
  return (
    <section>
      <SectionHeader title="Migration Roadmap" description="Phased modernization plan with timeline and dependencies" size="lg" />
      <div className="mt-4 space-y-4">
        <MigrationTimelineChart waves={waves} />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {waves.map((wave) => (
            <WaveCard key={wave.id} wave={wave} />
          ))}
        </div>
      </div>
    </section>
  );
}
