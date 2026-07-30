import { SectionHeader } from '@/components/ui/SectionHeader';
import { ExplainabilityCard } from '@/components/cards/ExplainabilityCard';
import { Badge } from '@/components/ui/Badge';
import { ConfidenceBadge } from '@/components/ui/StatusBadge';
import type { AnalysisResult } from '@/types/api';
import type { ExplainabilityEntry, ConfidenceFactor } from '@/types/dashboard';

function buildExplainabilityEntries(analysis: AnalysisResult): ExplainabilityEntry[] {
  const recs = (analysis.explainability as any)?.recommendations || [];
  const services = analysis.service_boundaries || [];

  if (recs.length > 0) {
    return recs.map((rec: any, i: number) => ({
      id: `exp-${i}`,
      service: rec.service,
      primaryReason: rec.primary_reason || 'Service boundary analysis',
      secondaryReasons: rec.secondary_reasons || [],
      evidence: {
        codeIsolation: `Cohesion: ${services.find((s) => s.name === rec.service)?.cohesion_score || 0}%`,
        lowCoupling: `Coupling: ${services.find((s) => s.name === rec.service)?.coupling_score || 0}%`,
        databaseIndependence: `${services.find((s) => s.name === rec.service)?.database_tables.length || 0} tables`,
        businessAlignment: rec.service.includes('Notification') ? 'Customer Communication' : 'Business Capability',
      },
      tradeoffs: {
        pros: ['Independent deployment', 'Technology flexibility', 'Scalability'],
        cons: ['Additional infrastructure', 'Operational complexity', 'Network overhead'],
      },
      alternatives: ['Keep as monolith', 'Shared library', 'Managed service'],
      impact: {
        business: `Enables ${rec.service} to evolve independently`,
        technical: rec.migration_complexity || 'Medium complexity',
        risk: rec.migration_complexity === 'high' ? 'High' : rec.migration_complexity === 'low' ? 'Low' : 'Medium',
      },
      confidence: rec.confidence || 75,
      confidenceFactors: [
        { id: 'code', name: 'Code Isolation', score: services.find((s) => s.name === rec.service)?.cohesion_score || 0, weight: 25, description: 'Module cohesion' },
        { id: 'coupling', name: 'Low Coupling', score: 100 - (services.find((s) => s.name === rec.service)?.coupling_score || 0), weight: 25, description: 'Inter-service independence' },
        { id: 'db', name: 'DB Independence', score: 60, weight: 20, description: 'Database separation feasibility' },
        { id: 'biz', name: 'Business Fit', score: 70, weight: 20, description: 'Business capability alignment' },
        { id: 'risk', name: 'Risk Profile', score: 65, weight: 10, description: 'Overall risk assessment' },
      ] as ConfidenceFactor[],
    }));
  }

  return services.map((svc, i) => ({
    id: `exp-${i}`,
    service: svc.name,
    primaryReason: svc.readiness === 'green'
      ? `Strong candidate with ${svc.cohesion_score}% cohesion and ${svc.confidence}% confidence`
      : svc.readiness === 'yellow'
      ? `Moderate readiness — coupling at ${svc.coupling_score}% needs attention`
      : `High-risk service requiring significant decomposition`,
    secondaryReasons: [
      `${svc.classes.length} classes across ${svc.packages.length} packages`,
      `${svc.api_endpoints.length} API endpoints`,
      `${svc.database_tables.length} database tables`,
    ],
    evidence: {
      codeIsolation: `Cohesion: ${svc.cohesion_score}%`,
      lowCoupling: `Coupling: ${svc.coupling_score}%`,
      databaseIndependence: `${svc.database_tables.length} shared tables`,
      businessAlignment: svc.business_capability || 'Unclassified',
    },
    tradeoffs: {
      pros: ['Independent deployment', 'Team autonomy', 'Technology flexibility'],
      cons: ['Infrastructure cost', 'Operational overhead', 'Distributed complexity'],
    },
    alternatives: ['Strangler fig pattern', 'Branch by abstraction', 'Database per service'],
    impact: {
      business: `Improves ${svc.business_capability || 'operational'} agility`,
      technical: `${svc.readiness === 'green' ? 'Low' : 'High'} migration complexity`,
      risk: `${svc.risk_level.charAt(0).toUpperCase() + svc.risk_level.slice(1)} risk level`,
    },
    confidence: svc.confidence,
    confidenceFactors: [] as ConfidenceFactor[],
  }));
}

export function ExplainabilityCenter({ analysis }: { analysis: AnalysisResult }) {
  const entries = buildExplainabilityEntries(analysis);
  const businessCapabilities = (analysis.explainability as any)?.business_capabilities || [];

  return (
    <section>
      <SectionHeader
        title="Explainability Center"
        description="AI decision transparency and evidence"
        action={<Badge variant="outline">{entries.length} analyses</Badge>}
      />

      {businessCapabilities.length > 0 && (
        <div className="bg-card rounded-xl border p-4 mb-4">
          <h3 className="text-sm font-semibold text-foreground mb-2">Business Capabilities Detected</h3>
          <div className="flex flex-wrap gap-2">
            {businessCapabilities.map((cap: string, i: number) => (
              <Badge key={i} variant="secondary">{cap}</Badge>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-3">
        {entries.map((entry) => (
          <ExplainabilityCard key={entry.id} data={entry} />
        ))}
      </div>
    </section>
  );
}
