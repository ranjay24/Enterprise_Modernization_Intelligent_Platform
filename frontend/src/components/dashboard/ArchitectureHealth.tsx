import type { HealthMetric } from '@/types/dashboard';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { cn } from '@/utils/cn';
import { getHealthStatus } from '@/utils/formatters';

function HealthCard({ data }: { data: HealthMetric }) {
  const valuePct = Math.min(100, Math.max(0, (data.value / data.maxValue) * 100));

  const isDebt = (data.id && data.id.includes('debt')) || (data.title && data.title.toLowerCase().includes('debt'));
  const status = isDebt ? getHealthStatus(data.id || data.title, data.value) : (data.status || getHealthStatus(data.id || data.title, data.value));

  const barColor = status === 'healthy' ? 'bg-success' :
    status === 'warning' ? 'bg-warning' : 'bg-danger';

  const statusColor = status === 'healthy' ? 'text-success' :
    status === 'warning' ? 'text-warning' : 'text-danger';

  const statusDot = status === 'healthy' ? 'bg-success' :
    status === 'warning' ? 'bg-warning' : 'bg-danger';

  return (
    <div className="rounded-xl border bg-card p-4 hover:shadow-sm transition-all duration-fast">
      <div className="flex items-start justify-between mb-3">
        <h4 className="text-sm font-semibold text-foreground">{data.title}</h4>
        <span className={cn('inline-flex items-center gap-1.5 text-xs font-medium', statusColor)}>
          <span className={cn('w-1.5 h-1.5 rounded-full', statusDot)} />
          {status}
        </span>
      </div>
      <div className="flex items-baseline gap-1 mb-3">
        <span className="text-2xl font-bold text-foreground tabular-nums">{data.value}</span>
        <span className="text-xs text-muted-foreground">/ {data.maxValue}</span>
      </div>
      <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden">
        <div className={cn('h-full rounded-full transition-all duration-700', barColor)} style={{ width: `${valuePct}%` }} />
      </div>
      <p className="text-xs text-muted-foreground/70 mt-2 line-clamp-1">{data.description}</p>
    </div>
  );
}

export function ArchitectureHealth({ data }: { data: HealthMetric[] }) {
  return (
    <section>
      <SectionHeader title="Architecture Health" description="System health and quality metrics" size="lg" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
        {data.map((metric) => (
          <HealthCard key={metric.id} data={metric} />
        ))}
      </div>
    </section>
  );
}
