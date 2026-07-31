import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, CheckCircle2, Calendar, BarChart3 } from 'lucide-react';
import { useResultsData } from '@/hooks/useResultsData';
import { formatConfidence } from '@/utils/formatters';
import { ExecutiveSummary } from '@/components/results/ExecutiveSummary';
import { ReadinessBreakdownSection } from '@/components/results/ReadinessBreakdown';
import { BusinessCapabilityMap } from '@/components/results/BusinessCapabilityMap';
import { ArchitectureIntelligence } from '@/components/results/ArchitectureIntelligence';
import { ConfidenceCenter } from '@/components/results/ConfidenceCenter';
import { RiskHeatmap } from '@/components/results/RiskHeatmap';
import { MicroserviceRecommendations } from '@/components/results/MicroserviceRecommendations';
import { MigrationRoadmap } from '@/components/results/MigrationRoadmap';
import { ADRCenter } from '@/components/results/ADRCenter';
import { ExplainabilityCenter } from '@/components/results/ExplainabilityCenter';
import { TechnicalDebtCenter } from '@/components/results/TechnicalDebtCenter';
import { CostAndROI } from '@/components/results/CostAndROI';
import { ValidationSummary } from '@/components/results/ValidationSummary';
import { GeneratedArtifacts } from '@/components/results/GeneratedArtifacts';
import { ExportCenter } from '@/components/results/ExportCenter';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/common/LoadingSkeleton';
import { cn } from '@/utils/cn';
import { Badge } from '@/components/ui/Badge';

export default function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const { data, isLoading, isError } = useResultsData(jobId);

  if (isLoading) {
    return (
      <div className="p-6 lg:p-8 max-w-[1440px] mx-auto space-y-6">
        <Skeleton className="h-4 w-24 rounded-lg" />
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="p-6 lg:p-8 max-w-[1440px] mx-auto">
        <Link to="/jobs" className="inline-flex items-center gap-1.5 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] mb-6">
          <ArrowLeft className="w-4 h-4" /> Back to Jobs
        </Link>
        <div className="text-center py-20">
          <div className="w-14 h-14 rounded-2xl bg-[var(--danger-bg)] flex items-center justify-center mx-auto mb-4">
            <BarChart3 className="w-7 h-7 text-[var(--risk)]" />
          </div>
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-1">No results found</h3>
          <p className="text-sm text-[var(--text-secondary)] mb-4">This job may still be processing or the results were not found.</p>
          <Link to="/jobs"><Button variant="outline" className="gap-2"><ArrowLeft className="w-4 h-4" /> Back to Jobs</Button></Link>
        </div>
      </div>
    );
  }

  const { analysis, confidence, riskHeatmap, recommendations, validation, artifacts, exports: exportOptions } = data;
  const overallScore = typeof analysis.readiness?.overall === 'number' ? analysis.readiness.overall : 0;
  const scoreColor = overallScore >= 70 ? 'text-[var(--success)]' : overallScore >= 40 ? 'text-[var(--warning)]' : 'text-[var(--risk)]';

  return (
    <div className="p-6 lg:p-8 max-w-[1440px] mx-auto space-y-8">
      {/* Top nav */}
      <Link
        to="/jobs"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors w-fit"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Jobs
      </Link>

      {/* Hero header */}
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-6 shadow-sm">
        <div className="flex items-start justify-between gap-6">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="success" size="sm">
                <CheckCircle2 className="w-3 h-3 mr-1" /> Analysis Complete
              </Badge>
            </div>
            <h1 className="text-[var(--font-size-3xl)] font-bold tracking-tight text-[var(--text-primary)] mb-1">
              Enterprise Modernization Intelligence
            </h1>
            <p className="text-sm text-[var(--text-secondary)]">
              Analysis completed{' '}
              {analysis.created_at ? new Date(analysis.created_at).toLocaleString() : 'Recently'}
            </p>
          </div>
          <div className="text-right shrink-0">
            <div className={cn('text-4xl font-bold tabular-nums', scoreColor)}>
              {overallScore}
              <span className="text-lg font-normal text-[var(--text-muted)]">/100</span>
            </div>
            <div className="text-sm text-[var(--text-secondary)] mt-1">
              Confidence: <span className="font-semibold text-[var(--text-primary)]">{formatConfidence(analysis.readiness?.confidence)}%</span>
            </div>
          </div>
        </div>

        {/* Quick stat row */}
        <div className="grid grid-cols-4 gap-px bg-[var(--border-subtle)] rounded-lg overflow-hidden mt-5">
          {[
            { label: 'Service Boundaries', value: analysis.service_boundaries?.length ?? 0 },
            { label: 'ADRs Generated', value: analysis.adrs?.length ?? 0 },
            { label: 'Migration Waves', value: analysis.migration_waves?.length ?? 0 },
            { label: 'Annual Savings', value: analysis.cost_comparison?.annual_savings ? `$${(analysis.cost_comparison.annual_savings / 1000).toFixed(0)}k` : '-' },
          ].map((stat) => (
            <div key={stat.label} className="bg-[var(--bg-card)] p-3 text-center">
              <div className="text-lg font-bold text-[var(--text-primary)] tabular-nums">{stat.value}</div>
              <div className="text-[10px] text-[var(--text-muted)] mt-0.5">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* All result sections */}
      <ExecutiveSummary analysis={analysis} />
      <ReadinessBreakdownSection readiness={analysis.readiness} />
      <BusinessCapabilityMap services={analysis.service_boundaries} />
      <ArchitectureIntelligence analysis={analysis} />
      <ConfidenceCenter data={confidence} />
      <RiskHeatmap entries={riskHeatmap} />
      <MicroserviceRecommendations recommendations={recommendations} />
      <MigrationRoadmap waves={analysis.migration_waves} />
      <ADRCenter adrs={analysis.adrs} />
      <ExplainabilityCenter analysis={analysis} />
      <TechnicalDebtCenter analysis={analysis} />
      <CostAndROI analysis={analysis} />
      <ValidationSummary checkpoints={validation} />
      <GeneratedArtifacts artifacts={artifacts} />
      <ExportCenter exports={exportOptions} />
    </div>
  );
}
