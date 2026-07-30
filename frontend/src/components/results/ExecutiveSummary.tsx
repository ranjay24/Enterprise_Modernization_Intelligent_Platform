import { Target, Shield, Brain, Layers, DollarSign, TrendingUp } from 'lucide-react';
import { cn } from '@/utils/cn';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { Badge } from '@/components/ui/Badge';
import { getScore, formatConfidence } from '@/utils/formatters';
import type { AnalysisResult } from '@/types/api';

const kpis = [
  { key: 'readiness', label: 'Overall Readiness', icon: Target, color: 'blue' as const, format: (r: AnalysisResult) => `${getScore(r.readiness?.overall)}%` },
  { key: 'confidence', label: 'AI Confidence', icon: Brain, color: 'purple' as const, format: (r: AnalysisResult) => `${formatConfidence(r.readiness?.confidence)}%` },
  { key: 'services', label: 'Services Identified', icon: Layers, color: 'cyan' as const, format: (r: AnalysisResult) => String((r.service_boundaries || []).length) },
  { key: 'adrs', label: 'ADRs Generated', icon: Shield, color: 'green' as const, format: (r: AnalysisResult) => String((r.adrs || []).length) },
  { key: 'savings', label: 'Monthly Savings', icon: DollarSign, color: 'green' as const, format: (r: AnalysisResult) => `$${(r.cost_comparison?.monthly_savings || 0).toLocaleString()}` },
];

const iconBg = {
  blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
  green: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
  purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
  cyan: 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-400',
};

export function ExecutiveSummary({ analysis }: { analysis: AnalysisResult }) {
  const cost = analysis.cost_comparison || {};
  const currentMonthly = cost.current_monthly || 0;
  const monthlySavings = cost.monthly_savings || 0;
  const overall = getScore(analysis.readiness?.overall);
  const savingsPercent = currentMonthly > 0
    ? Math.round((monthlySavings / currentMonthly) * 100)
    : 0;

  return (
    <section>
      <SectionHeader
        title="Executive Summary"
        description="Key findings from the modernization analysis"
        action={
          <Badge variant={overall >= 60 ? 'success' : overall >= 35 ? 'warning' : 'destructive'}>
            {overall >= 60 ? 'Ready' : overall >= 35 ? 'Needs Work' : 'Not Ready'}
          </Badge>
        }
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          const value = kpi.format(analysis);
          return (
            <article
              key={kpi.key}
              className={cn(
                'bg-card rounded-xl border p-4 border-l-4 hover:shadow-md transition-all hover:scale-[1.02]',
                kpi.key === 'readiness' && (overall >= 60 ? 'border-l-green-500' : overall >= 35 ? 'border-l-yellow-500' : 'border-l-red-500'),
                kpi.key === 'confidence' && 'border-l-purple-500',
                kpi.key === 'services' && 'border-l-cyan-500',
                kpi.key === 'adrs' && 'border-l-green-500',
                kpi.key === 'savings' && 'border-l-green-500',
              )}
            >
              <div className="flex items-start justify-between mb-3">
                <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', iconBg[kpi.color])}>
                  <Icon className="w-5 h-5" />
                </div>
                {kpi.key === 'savings' && savingsPercent > 0 && (
                  <span className="inline-flex items-center gap-0.5 text-xs text-green-600">
                    <TrendingUp className="w-3 h-3" /> {savingsPercent}%
                  </span>
                )}
              </div>
              <div className="text-sm text-muted-foreground mb-1">{kpi.label}</div>
              <div className="text-2xl font-bold text-foreground">{value}</div>
            </article>
          );
        })}
      </div>
      {analysis.readiness?.summary && (
        <div className="mt-4 bg-card rounded-xl border p-4">
          <p className="text-sm text-muted-foreground">{analysis.readiness.summary}</p>
        </div>
      )}
    </section>
  );
}
