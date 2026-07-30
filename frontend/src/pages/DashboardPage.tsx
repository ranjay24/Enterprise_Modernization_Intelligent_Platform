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
import { Upload, ArrowRight, Database, Package, Shield, FileText, DollarSign, AlertTriangle, Layers } from 'lucide-react';

export default function DashboardPage() {
  const { demoMode } = useAppStore();

  if (!demoMode) {
    return (
      <div className="p-6 lg:p-8 max-w-[1440px] mx-auto">
        <div className="flex items-center justify-between mb-8">
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
      </div>
    );
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
        <Link to="/upload">
          <Button variant="primary" className="gap-2">
            <Upload className="w-4 h-4" />
            New Analysis
          </Button>
        </Link>
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
