import type { AnalysisResult } from '@/types/api';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { CostBreakdownCard } from '@/components/cards/CostBreakdownCard';
import { CostTrendChart } from '@/components/charts/CostTrendChart';
import { Badge } from '@/components/ui/Badge';
import type { CostBreakdownData, ChartDataPoint } from '@/types/dashboard';

function apiCostToBreakdown(analysis: AnalysisResult): CostBreakdownData {
  const cost = analysis.cost_comparison || {};
  const currentMonthly = cost.current_monthly || 0;
  const postMonthly = cost.post_migration_monthly || 0;
  const breakdownCurrent = cost.breakdown_current || {};
  const breakdownPost = cost.breakdown_post || {};
  return {
    current: {
      monthly: currentMonthly,
      breakdown: {
        compute: breakdownCurrent.compute || currentMonthly * 0.42,
        storage: breakdownCurrent.storage || currentMonthly * 0.15,
        networking: breakdownCurrent.networking || currentMonthly * 0.11,
        operations: breakdownCurrent.operations || currentMonthly * 0.22,
        licensing: breakdownCurrent.licensing || currentMonthly * 0.10,
      },
    },
    projected: {
      monthly: postMonthly,
      breakdown: {
        compute: breakdownPost.compute || postMonthly * 0.41,
        storage: breakdownPost.storage || postMonthly * 0.15,
        networking: breakdownPost.networking || postMonthly * 0.11,
        operations: breakdownPost.operations || postMonthly * 0.22,
        licensing: breakdownPost.licensing || postMonthly * 0.11,
      },
    },
    savings: {
      monthly: cost.monthly_savings || 0,
      annual: cost.annual_savings || 0,
      percentage: currentMonthly > 0 ? Math.round(((cost.monthly_savings || 0) / currentMonthly) * 100) : 0,
    },
    roi: {
      paybackPeriod: `${cost.payback_months || 0} months`,
      breakEvenMonths: cost.payback_months || 0,
      totalSavings3Year: (cost.annual_savings || 0) * 3,
    },
  };
}

function buildCostChart(analysis: AnalysisResult): ChartDataPoint[] {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const cost = analysis.cost_comparison || {};
  const current = cost.current_monthly || 0;
  const projected = cost.post_migration_monthly || 0;
  return months.map((m, i) => ({
    name: m,
    current,
    projected: i < 3 ? current : current - ((current - projected) * (i - 2) / 9),
  }));
}

export function CostAndROI({ analysis }: { analysis: AnalysisResult }) {
  const costData = apiCostToBreakdown(analysis);
  const chartData = buildCostChart(analysis);
  const impact = (analysis.cost_comparison || {}).migration_impact;

  return (
    <section>
      <SectionHeader
        title="Cost & ROI"
        description="Financial impact analysis"
        action={
          <Badge variant="success">
            ${((analysis.cost_comparison || {}).monthly_savings || 0).toLocaleString()}/mo savings
          </Badge>
        }
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <CostBreakdownCard data={costData} />
        <CostTrendChart data={chartData} />
      </div>

      {impact && (
        <div className="bg-card rounded-xl border p-5">
          <h3 className="font-semibold text-foreground text-sm mb-4">Migration Impact</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
            {[
              { label: 'Services', value: impact.total_services },
              { label: 'Waves', value: impact.total_waves },
              { label: 'Timeline', value: `${impact.estimated_timeline_weeks}w` },
              { label: 'Engineers', value: impact.total_engineers_needed },
            ].map((stat) => (
              <div key={stat.label} className="text-center p-3 bg-muted rounded-lg">
                <div className="text-xl font-bold text-primary">{stat.value}</div>
                <div className="text-xs text-muted-foreground">{stat.label}</div>
              </div>
            ))}
          </div>
          {impact.risk_summary && (
            <p className="text-xs text-muted-foreground">{impact.risk_summary}</p>
          )}
        </div>
      )}
    </section>
  );
}
