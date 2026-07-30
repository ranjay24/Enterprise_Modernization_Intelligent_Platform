import type { ReadinessBreakdown as ReadinessBreakdownType } from '@/types/dashboard';
import { ReadinessRadar } from '@/components/charts/ReadinessRadar';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { cn } from '@/utils/cn';

const dimIcons: Record<string, string> = {
  Code2: 'CQ', Building2: 'AR', Cloud: 'CR', GitBranch: 'SS', Database: 'DC', FileText: 'DO',
};

const scoreColors = (score: number) => {
  if (score >= 70) return 'bg-success/10 text-success';
  if (score >= 40) return 'bg-warning/10 text-warning';
  return 'bg-danger/10 text-danger';
};

const barColor = (score: number) => {
  if (score >= 70) return 'bg-success';
  if (score >= 40) return 'bg-warning';
  return 'bg-danger';
};

export function ReadinessBreakdown({ data }: { data: ReadinessBreakdownType }) {
  return (
    <section>
      <SectionHeader title="Readiness Breakdown" description="Six-dimension modernization readiness assessment" size="lg" />
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 mt-4">
        <div className="lg:col-span-2">
          <ReadinessRadar data={data} />
        </div>
        <div className="lg:col-span-3 bg-card rounded-xl border p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-foreground">Dimension Scores</h3>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>Overall</span>
              <span className={cn(
                'px-2 py-0.5 rounded text-xs font-bold tabular-nums',
                scoreColors(data.overall)
              )}>{data.overall}%</span>
              <span className="text-border">|</span>
              <span>Confidence</span>
              <span className="px-2 py-0.5 rounded text-xs font-bold tabular-nums bg-info-bg text-info">{data.confidence}%</span>
            </div>
          </div>
          <div className="space-y-2.5">
            {data.dimensions.map((dim) => (
              <div key={dim.id} className="group">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="w-6 h-6 rounded bg-muted flex items-center justify-center text-[10px] font-bold text-muted-foreground shrink-0">
                      {dimIcons[dim.icon] || '?'}
                    </span>
                    <span className="text-xs font-medium text-foreground truncate">{dim.name}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] text-muted-foreground">{dim.weight}%</span>
                    <span className={cn(
                      'w-6 text-right text-[11px] font-bold tabular-nums',
                      dim.score >= 70 ? 'text-success' : dim.score >= 40 ? 'text-warning' : 'text-danger'
                    )}>
                      {dim.score}
                    </span>
                  </div>
                </div>
                <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden">
                  <div
                    className={cn('h-full rounded-full transition-all duration-700 ease-out', barColor(dim.score))}
                    style={{ width: `${dim.score}%` }}
                  />
                </div>
                {dim.evidence && (
                  <p className="text-[10px] text-muted-foreground/60 mt-1 leading-tight line-clamp-1">{dim.evidence}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
