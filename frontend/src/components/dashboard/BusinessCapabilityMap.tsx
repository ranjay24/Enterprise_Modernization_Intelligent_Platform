import type { BusinessCapability } from '@/types/dashboard';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { cn } from '@/utils/cn';

const capColors: Record<string, string> = {
  blue: 'bg-info-bg text-info border-info/20',
  green: 'bg-success-bg text-success border-success/20',
  yellow: 'bg-warning-bg text-warning border-warning/20',
  red: 'bg-danger-bg text-danger border-danger/20',
  purple: 'bg-[hsl(var(--stage-ai-boundaries)/0.1)] text-[hsl(var(--stage-ai-boundaries))] border-[hsl(var(--stage-ai-boundaries)/0.2)]',
  cyan: 'bg-[hsl(var(--stage-ai-readiness)/0.1)] text-[hsl(var(--stage-ai-readiness))] border-[hsl(var(--stage-ai-readiness)/0.2)]',
};

function CapabilityCard({ data }: { data: BusinessCapability }) {
  return (
    <div className="rounded-xl border bg-card p-4 hover:shadow-sm transition-all duration-fast">
      <div className="flex items-start justify-between mb-3">
        <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center border', capColors[data.color])}>
          <span className="text-sm font-bold">{data.name[0]}</span>
        </div>
        <div className={cn(
          'px-2 py-0.5 rounded text-[10px] font-semibold',
          data.risk === 'low' ? 'bg-success-bg text-success' :
          data.risk === 'medium' ? 'bg-warning-bg text-warning' :
          'bg-danger-bg text-danger'
        )}>
          {data.risk}
        </div>
      </div>
      <h4 className="text-sm font-semibold text-foreground mb-0.5">{data.name}</h4>
      <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{data.description}</p>
      <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
        <span>Readiness <span className="font-semibold text-foreground">{data.readiness}%</span></span>
        <span>Confidence <span className="font-semibold text-foreground">{data.confidence}%</span></span>
        <span>{data.classes} classes</span>
      </div>
    </div>
  );
}

export function BusinessCapabilityMap({ data }: { data: BusinessCapability[] }) {
  return (
    <section>
      <SectionHeader title="Business Capability Map" description="Service boundary analysis and domain mapping" size="lg" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
        {data.map((cap) => (
          <CapabilityCard key={cap.id} data={cap} />
        ))}
      </div>
    </section>
  );
}
