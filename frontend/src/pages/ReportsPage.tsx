import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { DollarSign, ArrowRight, BarChart3, FileText, Layers, Brain } from 'lucide-react';
import { listJobs, getAnalysisResults } from '@/services/jobService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ScoreGauge } from '@/components/cards';
import { EmptyState } from '@/components/common/EmptyState';
import { TableSkeleton } from '@/components/common/LoadingSkeleton';
import { formatCurrency } from '@/utils/formatters';
import { cn } from '@/utils/cn';
import { Badge } from '@/components/ui/Badge';

export default function ReportsPage() {
  const { data: jobsData, isLoading: jobsLoading } = useQuery({
    queryKey: ['jobs'], queryFn: listJobs, staleTime: 30000,
  });

  const completedJobs = (jobsData?.jobs || []).filter((j) =>
    ['analysis_complete', 'generation_complete', 'generation_with_warnings'].includes(j.status)
  );
  const latestJob = completedJobs[0];

  const { data: results, isLoading: resultsLoading } = useQuery({
    queryKey: ['analysis', latestJob?.job_id],
    queryFn: () => getAnalysisResults(latestJob!.job_id),
    enabled: !!latestJob, staleTime: 60000,
  });

  const isLoading = jobsLoading || resultsLoading;

  if (isLoading) return <div className="p-6 lg:p-8 max-w-7xl mx-auto"><TableSkeleton rows={5} /></div>;

  if (!results) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto">
        <h1 className="text-display text-foreground mb-1">Reports</h1>
        <p className="text-body-sm text-muted-foreground mb-8">Executive summary and financial analysis</p>
        <EmptyState
          icon={<BarChart3 className="w-8 h-8" />}
          title="No report data"
          description="Run an analysis to generate executive reports."
          action={<Link to="/upload"><Button variant="primary">Analyze Codebase</Button></Link>}
        />
      </div>
    );
  }

  const cost = results.cost_comparison;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-display text-foreground mb-1">Reports</h1>
        <p className="text-body-sm text-muted-foreground">Executive summary and financial analysis</p>
      </div>

      {/* Readiness Assessment */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-primary" />
            Readiness Assessment
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <ScoreGauge score={results.readiness.code_quality} label="Code Quality" weight={25} />
            <ScoreGauge score={results.readiness.architecture} label="Architecture" weight={20} />
            <ScoreGauge score={results.readiness.cloud_readiness} label="Cloud Readiness" weight={20} />
            <ScoreGauge score={results.readiness.service_separation} label="Service Separation" weight={20} />
            <ScoreGauge score={results.readiness.database_coupling} label="Database Coupling" weight={10} />
            <ScoreGauge score={results.readiness.documentation} label="Documentation" weight={5} />
          </div>
          {results.readiness.summary && (
            <div className="mt-4 p-4 rounded-lg bg-muted/50 border text-sm text-muted-foreground whitespace-pre-wrap">
              {results.readiness.summary}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Cost Analysis */}
      {cost && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-success" />
              Cost Analysis
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="rounded-xl border bg-card p-5">
                <p className="text-xs text-muted-foreground mb-1">Current Monthly</p>
                <p className="text-h2 text-foreground tabular-nums">{formatCurrency(cost.current_monthly)}<span className="text-sm font-normal text-muted-foreground">/mo</span></p>
              </div>
              <div className="rounded-xl border bg-card p-5">
                <p className="text-xs text-muted-foreground mb-1">Post-Migration Monthly</p>
                <p className="text-h2 text-success tabular-nums">{formatCurrency(cost.post_migration_monthly)}<span className="text-sm font-normal text-muted-foreground">/mo</span></p>
              </div>
            </div>
            <div className="rounded-xl border border-success/20 bg-success-bg/50 p-5">
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: 'Monthly Savings', value: formatCurrency(cost.monthly_savings) },
                  { label: 'Annual Savings', value: formatCurrency(cost.annual_savings) },
                  { label: 'Payback Period', value: `${cost.payback_months} months` },
                ].map((item) => (
                  <div key={item.label} className="text-center">
                    <p className="text-xl font-bold text-success tabular-nums">{item.value}</p>
                    <p className="text-xs text-success/70 mt-0.5">{item.label}</p>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Analysis Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-info" />
            Analysis Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Services', value: (results.service_boundaries || []).length, icon: Layers, color: 'text-info bg-info-bg' },
              { label: 'ADRs', value: (results.adrs || []).length, icon: FileText, color: 'text-success bg-success-bg' },
              { label: 'Migration Waves', value: (results.migration_waves || []).length, icon: Layers, color: 'text-warning bg-warning-bg' },
              { label: 'Readiness Score', value: typeof results.readiness?.overall === 'number' ? `${results.readiness.overall}%` : '0%', icon: Brain, color: 'text-[hsl(var(--stage-ai-boundaries))] bg-[hsl(var(--stage-ai-boundaries)/0.1)]' },
            ].map((stat) => (
              <div key={stat.label} className="rounded-lg border bg-card p-4 text-center">
                <stat.icon className={cn('w-5 h-5 mx-auto mb-2', stat.color.split(' ')[1])} />
                <p className="text-xl font-bold text-foreground tabular-nums">{stat.value}</p>
                <p className="text-[10px] text-muted-foreground">{stat.label}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {latestJob && (
        <Link to={`/jobs/${latestJob.job_id}/results`} className="inline-block">
          <Button variant="outline" className="gap-2">
            View Full Results <ArrowRight className="w-4 h-4" />
          </Button>
        </Link>
      )}
    </div>
  );
}
