import { useAppStore } from '@/store/useAppStore';
import {
  kpiCards,
  readinessBreakdown,
  healthMetrics,
  serviceReadiness,
  migrationWaves,
  aiRecommendations,
  debtItems,
  costComparison,
  monthlyCostChart,
  recentAnalyses,
  quickActions,
} from '@/data/mockDashboard';
import { businessCapabilities } from '@/data/mockCapabilities';
import { explainabilityEntries, adrPreviews } from '@/data/mockExplainability';
import { ExecutiveSummary } from '@/components/dashboard/ExecutiveSummary';
import { ReadinessBreakdown } from '@/components/dashboard/ReadinessBreakdown';
import { BusinessCapabilityMap } from '@/components/dashboard/BusinessCapabilityMap';
import { ArchitectureHealth } from '@/components/dashboard/ArchitectureHealth';
import { ServiceReadinessMatrix } from '@/components/dashboard/ServiceReadinessMatrix';
import { MigrationTimeline } from '@/components/dashboard/MigrationTimeline';
import { AIRecommendations } from '@/components/dashboard/AIRecommendations';
import { ExplainabilityPanel } from '@/components/dashboard/ExplainabilityPanel';
import { ADRPreview } from '@/components/dashboard/ADRPreview';
import { TechnicalDebt } from '@/components/dashboard/TechnicalDebt';
import { CostComparison } from '@/components/dashboard/CostComparison';
import { RecentAnalyses } from '@/components/dashboard/RecentAnalyses';
import { QuickActions } from '@/components/dashboard/QuickActions';
import { DashboardHero } from '@/components/dashboard/DashboardHero';
import { SummaryRow } from '@/components/dashboard/SummaryRow';
import { Button } from '@/components/ui/Button';
import { Link } from 'react-router-dom';
import { Upload, ArrowRight, Database, Package, Shield, FileText, DollarSign, AlertTriangle, Layers, FlaskConical } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { listJobs } from '@/services/jobService';
import { useAnalysisResults } from '@/hooks/useAnalysisResults';
import { STALE_TIME_MS } from '@/utils/constants';

const COMPLETED_STATUSES = ['analysis_complete', 'generation_complete', 'generation_with_warnings'];

const STATUS_LABELS: Record<string, string> = {
  queued: 'Queued',
  uploading: 'Uploaded',
  validating: 'Validating',
  analyzing: 'Analyzing',
  ai_processing: 'AI Processing',
  generating: 'Generating Code',
  generating_report: 'Generating Report',
  paused: 'Paused',
  analysis_complete: 'Analysis Complete',
  generation_complete: 'Completed',
  generation_with_warnings: 'Completed (with warnings)',
  deployed: 'Deployed',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

function statusBadgeClass(status: string): string {
  if (COMPLETED_STATUSES.includes(status)) return 'bg-[var(--success)]/10 text-[var(--success)]';
  if (status === 'failed') return 'bg-[var(--risk)]/10 text-[var(--risk)]';
  return 'bg-[var(--warning)]/10 text-[var(--warning)]';
}

function RealDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: listJobs,
    staleTime: STALE_TIME_MS,
    refetchOnWindowFocus: false,
  });

  const jobs = data?.jobs || [];
  const completed = jobs
    .filter((j) => COMPLETED_STATUSES.includes(j.status))
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
  const latest = completed[0];
  const inProgress = jobs.filter((j) => !COMPLETED_STATUSES.includes(j.status) && j.status !== 'failed');

  const results = useAnalysisResults(latest?.job_id);

  const analysis = results.data;
  const fmtMoney = (v: number | undefined) => `$${Math.round(Number(v || 0)).toLocaleString()}`;

  const stats = analysis
    ? [
        { label: 'Service Boundaries', value: `${analysis.service_boundaries.length}`, icon: Layers },
        { label: 'Readiness Score', value: `${Math.round(Number(analysis.readiness?.overall) || 0)}%`, icon: Shield },
        { label: 'Java Classes', value: `${Number(analysis.metrics?.total_classes) || 0}`, icon: Database },
        { label: 'Files Analyzed', value: `${Number(analysis.metrics?.total_files) || 0}`, icon: FileText },
        { label: 'ADRs', value: `${analysis.adrs?.length || 0}`, icon: FileText },
        { label: 'Migration Waves', value: `${analysis.migration_waves?.length || 0}`, icon: Layers },
        { label: 'Est. Monthly Savings', value: fmtMoney(analysis.cost_comparison?.monthly_savings), icon: DollarSign },
        { label: 'Payback Period', value: `${analysis.cost_comparison?.payback_months ?? '-'} mo`, icon: AlertTriangle },
      ]
    : [];

  const actionLinks = (jobId: string) => (
    <div className="flex items-center gap-3 mt-6 flex-wrap">
      <Link to="/jobs">
        <Button variant="secondary" className="gap-2"><ArrowRight className="w-4 h-4" />View All Jobs</Button>
      </Link>
      <Link to={`/results/${jobId}`}>
        <Button variant="secondary" className="gap-2"><ArrowRight className="w-4 h-4" />View Results</Button>
      </Link>
      <Link to={`/jobs/${jobId}/studio`}>
        <Button variant="primary" className="gap-2"><ArrowRight className="w-4 h-4" />Open Modernization Studio</Button>
      </Link>
      <span className="text-xs text-[var(--text-muted)] font-mono">{jobId}</span>
    </div>
  );

  return (
    <div className="p-6 lg:p-8 max-w-[1440px] mx-auto space-y-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[var(--font-size-3xl)] font-bold tracking-tight text-[var(--text-primary)] mb-1">Dashboard</h1>
          <p className="text-sm text-[var(--text-secondary)]">Enterprise Modernization Intelligence Platform</p>
        </div>
        <Link to="/upload">
          <Button variant="primary" className="gap-2">
            <Upload className="w-4 h-4" />
            Analyze Code
          </Button>
        </Link>
      </div>

      <QuickActions data={quickActions} />

      {isLoading ? (
        <div className="text-sm text-[var(--text-secondary)] py-8">Loading analyses…</div>
      ) : latest ? (
        <section className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-6">
          <div className="flex items-start justify-between mb-6 flex-wrap gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-muted)] mb-1">Latest completed analysis</p>
              <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1">
                {latest.filename.replace(/\.zip$/i, '').replace(/[-_]/g, ' ')}
              </h2>
              <p className="text-sm text-[var(--text-secondary)]">{new Date(latest.created_at).toLocaleString()}</p>
            </div>
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${statusBadgeClass(latest.status)}`}>
              {STATUS_LABELS[latest.status] || latest.status}
            </span>
          </div>

          {results.isLoading ? (
            <p className="text-sm text-[var(--text-secondary)] py-4">Loading analysis metrics…</p>
          ) : analysis ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {stats.map((s) => (
                  <div key={s.label} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
                    <s.icon className="w-4 h-4 text-[var(--text-muted)] mb-2" />
                    <p className="text-2xl font-bold text-[var(--text-primary)]">{s.value}</p>
                    <p className="text-xs text-[var(--text-secondary)] mt-1">{s.label}</p>
                  </div>
                ))}
              </div>
              {actionLinks(latest.job_id)}
            </>
          ) : (
            <>
              <p className="text-sm text-[var(--text-secondary)]">Analysis data unavailable for this job.</p>
              {actionLinks(latest.job_id)}
            </>
          )}
        </section>
      ) : jobs.length === 0 ? (
        <div className="mt-16 text-center max-w-lg mx-auto">
          <div className="w-16 h-16 rounded-2xl bg-[var(--bg-card)] flex items-center justify-center mx-auto mb-5 border border-[var(--border-subtle)]">
            <Upload className="w-8 h-8 text-[var(--text-muted)]" />
          </div>
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">No analyses yet</h3>
          <p className="text-sm text-[var(--text-secondary)] mb-6 leading-relaxed">
            Upload a Java monolith to analyze or enable Demo Mode to explore sample data.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Link to="/upload">
              <Button variant="primary" className="gap-2">
                <Upload className="w-4 h-4" />
                Upload Project
              </Button>
            </Link>
            <Button variant="secondary" onClick={() => useAppStore.getState().toggleDemoMode()}>
              Enable Demo Mode
            </Button>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-6">
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">Analyses in progress</h3>
          <ul className="space-y-2">
            {inProgress.map((j) => (
              <li key={j.job_id} className="flex items-center justify-between text-sm">
                <span className="text-[var(--text-primary)]">{j.filename}</span>
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${statusBadgeClass(j.status)}`}>
                  {STATUS_LABELS[j.status] || j.status}
                </span>
              </li>
            ))}
          </ul>
          <div className="mt-4">
            <Link to="/jobs">
              <Button variant="secondary" className="gap-2"><ArrowRight className="w-4 h-4" />View All Jobs</Button>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { demoMode } = useAppStore();

  if (!demoMode) {
    return <RealDashboard />;
  }

  const { overall, confidence } = readinessBreakdown;
  const scoreColor = overall >= 70 ? 'bg-[var(--success)]/10 text-[var(--success)]' : overall >= 40 ? 'bg-[var(--warning)]/10 text-[var(--warning)]' : 'bg-[var(--risk)]/10 text-[var(--risk)]';
  const statusLabel = overall >= 70 ? 'Low Risk' : overall >= 40 ? 'Moderate Risk' : 'High Risk';

  const heroStats = [
    { label: 'Java Classes', value: 173, icon: Database, color: 'text-[var(--accent-blue)]' },
    { label: 'Packages', value: 46, icon: Package, color: 'text-[var(--architecture)]' },
    { label: 'DB Tables', value: 30, icon: Database, color: 'text-[var(--analytics)]' },
    { label: 'God Classes', value: 10, icon: AlertTriangle, color: 'text-[var(--risk)]' },
    { label: 'Security Risks', value: 27, icon: Shield, color: 'text-[var(--warning)]' },
    { label: 'Annual Savings', value: '$180k', icon: DollarSign, color: 'text-[var(--success)]', unit: '' },
  ];

  const summaryStats = [
    { label: "Today's Analyses", value: 4, unit: '' },
    { label: 'Cloud Readiness Avg', value: overall, unit: '%' },
    { label: 'Projects', value: 12, unit: '' },
    { label: 'Security Findings', value: 27, unit: '' },
    { label: 'Migration Cost', value: 180, unit: 'k', format: (v: number) => `$${v}` },
    { label: 'Est. Savings', value: 50, unit: 'k', format: (v: number) => `$${v}` },
  ];

  return (
    <div className="p-6 lg:p-8 max-w-[1440px] mx-auto space-y-10">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[var(--font-size-3xl)] font-bold tracking-tight text-[var(--text-primary)] mb-1">Dashboard</h1>
          <p className="text-sm text-[var(--text-secondary)]">Platform overview and modernization intelligence</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-[var(--warning)]/10 text-[var(--warning)]">
            Demo data
          </span>
          <Link to="/upload">
            <Button variant="primary" className="gap-2">
              <Upload className="w-4 h-4" />
              New Analysis
            </Button>
          </Link>
        </div>
      </div>

      {/* Demo notice */}
      <div className="flex items-center gap-2 rounded-xl border border-[var(--warning)]/25 bg-[var(--warning)]/5 px-4 py-3">
        <FlaskConical className="w-4 h-4 text-[var(--warning)] shrink-0" />
        <p className="text-sm text-[var(--text-secondary)]">
          Demo Mode is on — every metric, chart, and recommendation below is{' '}
          <span className="font-semibold text-[var(--text-primary)]">sample data</span>, not from a real analysis.
        </p>
      </div>

      {/* Summary row — quiet, account-level numbers */}
      <SummaryRow stats={summaryStats} />

      {/* Hero section — glass surface with radial gauge */}
      <DashboardHero
        overallScore={overall}
        confidence={confidence}
        statusLabel={statusLabel}
        statusColor={scoreColor}
        stats={heroStats}
      />

      {/* Main content */}
      <ExecutiveSummary data={kpiCards} />
      <ReadinessBreakdown data={readinessBreakdown} />
      <BusinessCapabilityMap data={businessCapabilities} />
      <ArchitectureHealth data={healthMetrics} />
      <ServiceReadinessMatrix services={serviceReadiness} />
      <MigrationTimeline waves={migrationWaves} />
      <AIRecommendations data={aiRecommendations} />
      <ExplainabilityPanel data={explainabilityEntries} />
      <ADRPreview data={adrPreviews} />
      <TechnicalDebt data={debtItems} />
      <CostComparison breakdown={costComparison} chart={monthlyCostChart} />
      <RecentAnalyses data={recentAnalyses} />
      <QuickActions data={quickActions} />
    </div>
  );
}
