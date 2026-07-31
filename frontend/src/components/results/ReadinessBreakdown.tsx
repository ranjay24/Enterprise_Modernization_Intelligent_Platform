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

interface DimensionDetail {
  evidence?: string;
  evidence_bullets?: string[];
  categories?: { category: string; score: number; evidence: string }[];
}

function detailOf(value: unknown): DimensionDetail | null {
  if (value && typeof value === 'object' && 'score' in value) {
    return value as DimensionDetail;
  }
  return null;
}

function toRadarData(readiness: ReadinessScores): ReadinessBreakdown {
  return {
    overall: readiness.overall,
    confidence: readiness.confidence,
    dimensions: dimensions.map((d) => {
      const raw = readiness[d.key as keyof ReadinessScores];
      const detail = detailOf(raw);
      const score = getScore(raw);
      return {
        id: d.key,
        name: d.name,
        score,
        weight: d.weight,
        evidence: detail?.evidence || '',
        evidence_bullets: detail?.evidence_bullets || [],
        status: score >= 70 ? 'healthy' as const : score >= 40 ? 'warning' as const : 'critical' as const,
        icon: d.icon,
      };
    }),
  };
}

export function ReadinessBreakdownSection({ readiness }: { readiness: ReadinessScores }) {
  const radarData = toRadarData(readiness);
  const cloudDetail = detailOf(readiness.cloud_readiness);

  return (
    <section>
      <SectionHeader title="Readiness Breakdown" description="6-dimension readiness analysis with evidence" />
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
                {dim.evidence_bullets && dim.evidence_bullets.length > 0 ? (
                  <ul className="mt-1.5 pl-6 space-y-0.5">
                    {dim.evidence_bullets.map((bullet, i) => (
                      <li key={i} className="text-xs text-muted-foreground list-disc">
                        {bullet}
                      </li>
                    ))}
                  </ul>
                ) : dim.evidence ? (
                  <p className="text-xs text-muted-foreground mt-1.5 pl-6">{dim.evidence}</p>
                ) : null}
                {dim.id === 'cloud_readiness' && cloudDetail?.categories && (
                  <div className="mt-2 pl-6 space-y-1.5">
                    {cloudDetail.categories.map((cat) => (
                      <div key={cat.category}>
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-muted-foreground">{cat.category}</span>
                          <span className="font-medium text-foreground">{cat.score}/100</span>
                        </div>
                        <ProgressBar value={cat.score} className="h-1.5" />
                        {cat.evidence && (
                          <p className="text-[11px] text-muted-foreground mt-0.5">{cat.evidence}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
