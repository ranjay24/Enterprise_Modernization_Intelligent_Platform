import { cn } from '@/utils/cn';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { HealthCard } from '@/components/cards/HealthCard';
import { ReadinessBadge, RiskBadge } from '@/components/cards';
import type { AnalysisResult } from '@/types/api';
import type { HealthMetric } from '@/types/dashboard';
import type { GodClassMetric, CircularDependencyMetric, DeadCodeMetric } from '@/types/metrics';
import { getScore, getHealthStatus } from '@/utils/formatters';

function computeHealthMetrics(analysis: AnalysisResult): HealthMetric[] {
  const godClasses = (analysis.metrics?.god_classes || []) as GodClassMetric[];
  const circularDeps = (analysis.metrics?.circular_dependencies || []) as CircularDependencyMetric[];
  const deadCode = (analysis.metrics?.dead_code || []) as DeadCodeMetric[];
  const services = analysis.service_boundaries || [];
  const avgCohesion = services.length > 0
    ? Math.round(services.reduce((s, svc) => s + svc.cohesion_score, 0) / services.length)
    : 0;
  const avgCoupling = services.length > 0
    ? Math.round(services.reduce((s, svc) => s + svc.coupling_score, 0) / services.length)
    : 0;
  const archQualityScore = getScore(analysis.readiness?.architecture);
  const techDebtScore = Math.min(100, godClasses.length * 25 + circularDeps.length * 15 + deadCode.length * 3);

  return [
    {
      id: 'candidates', title: 'Microservice Candidates', value: services.filter((s) => s.readiness === 'green').length,
      maxValue: Math.max(services.length, 1), unit: `/${services.length}`, status: 'healthy',
      description: 'Services ready for extraction', icon: 'Puzzle',
    },
    {
      id: 'dep-health', title: 'Dependency Health', value: Math.max(0, 100 - circularDeps.length * 15),
      maxValue: 100, unit: '/100', status: circularDeps.length === 0 ? 'healthy' : circularDeps.length <= 2 ? 'warning' : 'critical',
      description: `${circularDeps.length} circular dependencies detected`, icon: 'Link',
    },
    {
      id: 'arch-quality', title: 'Architecture Quality', value: archQualityScore,
      maxValue: 100, unit: '/100', status: getHealthStatus('arch-quality', archQualityScore),
      description: 'Overall architectural soundness', icon: 'Layout',
    },
    {
      id: 'maintainability', title: 'Maintainability Index', value: avgCohesion,
      maxValue: 100, unit: '/100', status: getHealthStatus('maintainability', avgCohesion),
      description: `Average cohesion: ${avgCohesion}%`, icon: 'Wrench',
    },
    {
      id: 'tech-debt', title: 'Technical Debt Score', value: techDebtScore,
      maxValue: 100, unit: '/100', status: getHealthStatus('tech-debt', techDebtScore),
      description: `${godClasses.length} god classes, ${circularDeps.length} cycles`, icon: 'AlertTriangle',
    },
    {
      id: 'complexity', title: 'Code Complexity', value: Math.max(10, 100 - avgCoupling),
      maxValue: 100, unit: '/100', status: avgCoupling <= 40 ? 'healthy' : 'warning',
      description: `Average coupling: ${avgCoupling}%`, icon: 'Activity',
    },
  ];
}

export function ArchitectureIntelligence({ analysis }: { analysis: AnalysisResult }) {
  const healthMetrics = computeHealthMetrics(analysis);
  const services = analysis.service_boundaries || [];

  return (
    <section>
      <SectionHeader title="Architecture Intelligence" description="Service health and structural analysis" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {healthMetrics.map((metric) => (
          <HealthCard key={metric.id} data={metric} />
        ))}
      </div>

      <div className="bg-card rounded-xl border p-5">
        <h3 className="font-semibold text-foreground text-sm mb-4">Service Boundary Matrix</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-3 font-medium text-muted-foreground">Service</th>
                <th className="text-center py-2 px-3 font-medium text-muted-foreground">Ready</th>
                <th className="text-center py-2 px-3 font-medium text-muted-foreground">Risk</th>
                <th className="text-center py-2 px-3 font-medium text-muted-foreground">Cohesion</th>
                <th className="text-center py-2 px-3 font-medium text-muted-foreground">Coupling</th>
                <th className="text-center py-2 px-3 font-medium text-muted-foreground">Classes</th>
                <th className="text-center py-2 px-3 font-medium text-muted-foreground">APIs</th>
                <th className="text-center py-2 px-3 font-medium text-muted-foreground">Tables</th>
              </tr>
            </thead>
            <tbody>
              {services.map((svc) => (
                <tr key={svc.name} className="border-b last:border-0 hover:bg-accent/50 transition-colors">
                  <td className="py-2.5 px-3 font-medium text-foreground">{svc.name}</td>
                  <td className="py-2.5 px-3 text-center"><ReadinessBadge readiness={svc.readiness} /></td>
                  <td className="py-2.5 px-3 text-center"><RiskBadge risk={svc.risk_level} /></td>
                  <td className="py-2.5 px-3 text-center">
                    <span className={cn('font-medium', svc.cohesion_score >= 70 ? 'text-green-600' : svc.cohesion_score >= 40 ? 'text-yellow-600' : 'text-red-600')}>
                      {svc.cohesion_score}%
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <span className={cn('font-medium', svc.coupling_score <= 30 ? 'text-green-600' : svc.coupling_score <= 60 ? 'text-yellow-600' : 'text-red-600')}>
                      {svc.coupling_score}%
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center text-foreground">{svc.classes.length}</td>
                  <td className="py-2.5 px-3 text-center text-foreground">{svc.api_endpoints.length}</td>
                  <td className="py-2.5 px-3 text-center text-foreground">{svc.database_tables.length}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
