import type { ReadinessScores } from '@/types/api';
import { ReadinessRadar } from '@/components/charts/ReadinessRadar';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { StatusBadge } from '@/components/ui/StatusBadge';
import type { ReadinessBreakdown } from '@/types/dashboard';
import { getScore } from '@/utils/formatters';

const dimensions: { key: string; name: string; weight: number; icon: string }[] = [
  { key: 'code_quality', name: 'Code Quality', weight: 25, icon: '💻' },
  { key: 'architecture', name: 'Architecture', weight: 20, icon: '🏢' },
  { key: 'cloud_readiness', name: 'Cloud Readiness', weight: 20, icon: '☁️' },
  { key: 'service_separation', name: 'Service Separation', weight: 20, icon: '⑂' },
  { key: 'database_coupling', name: 'Database Coupling', weight: 10, icon: '🗄️' },
  { key: 'documentation', name: 'Documentation', weight: 5, icon: '📄' },
];

function toRadarData(readiness: ReadinessScores): ReadinessBreakdown {
  return {
    overall: readiness.overall,
    confidence: readiness.confidence,
    dimensions: dimensions.map((d, i) => {
      const raw = readiness[d.key as keyof ReadinessScores];
      const score = getScore(raw);
      return {
        id: d.key,
        name: d.name,
        score,
        weight: d.weight,
        evidence: typeof raw === 'object' && raw !== null && 'evidence' in raw ? (raw as { evidence: string }).evidence : '',
        status: score >= 70 ? 'healthy' as const : score >= 40 ? 'warning' as const : 'critical' as const,
        icon: d.icon,
      };
    }),
  };
}

export function ReadinessBreakdownSection({ readiness }: { readiness: ReadinessScores }) {
  const radarData = toRadarData(readiness);

  return (
    <section>
      <SectionHeader title="Readiness Breakdown" description="6-dimension readiness analysis" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ReadinessRadar data={radarData} />
        <div className="bg-card rounded-xl border p-5">
          <h3 className="font-semibold text-foreground text-sm mb-4">Dimension Scores</h3>
          <div className="space-y-3">
            {radarData.dimensions.map((dim) => (
              <div key={dim.id} className="bg-muted/50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">{dim.icon}</span>
                    <span className="text-xs font-medium text-foreground">{dim.name}</span>
                    <span className="text-xs text-muted-foreground">({dim.weight}%)</span>
                  </div>
                  <StatusBadge status={dim.status} />
                </div>
                <div className="flex items-center gap-2">
                  <ProgressBar value={dim.score} className="flex-1" />
                  <span className="text-xs font-bold text-foreground w-8 text-right">{dim.score}</span>
                </div>
                {dim.evidence && (
                  <p className="text-xs text-muted-foreground mt-1.5 pl-6">{dim.evidence}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
