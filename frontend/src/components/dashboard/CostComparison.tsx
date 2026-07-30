import type { CostBreakdownData, ChartDataPoint } from '@/types/dashboard';
import { CostTrendChart } from '@/components/charts/CostTrendChart';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { cn } from '@/utils/cn';
import { TrendingDown, DollarSign, Clock, PiggyBank } from 'lucide-react';

function StatBlock({ label, value, icon, color }: { label: string; value: string; icon: React.ReactNode; color: string }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="flex items-center gap-2 mb-1">
        <span className={cn('w-6 h-6 rounded flex items-center justify-center', color)}>{icon}</span>
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <span className="text-sm font-bold text-foreground tabular-nums">{value}</span>
    </div>
  );
}

export function CostComparison({ breakdown, chart }: { breakdown: CostBreakdownData; chart: ChartDataPoint[] }) {
  return (
    <section>
      <SectionHeader title="Cost Analysis" description="Current vs projected infrastructure costs" size="lg" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        <div className="lg:col-span-2 bg-card rounded-xl border p-5">
          <CostTrendChart data={chart} />
        </div>
        <div className="space-y-3">
          <div className="rounded-xl border bg-card p-4">
            <h4 className="text-sm font-semibold text-foreground mb-3">Cost Summary</h4>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Current Monthly</span>
                <span className="font-semibold text-foreground tabular-nums">${breakdown.current.monthly.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Projected Monthly</span>
                <span className="font-semibold text-success tabular-nums">${breakdown.projected.monthly.toLocaleString()}</span>
              </div>
              <div className="border-t pt-2 mt-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-foreground">Monthly Savings</span>
                  <span className="font-bold text-success tabular-nums">${breakdown.savings.monthly.toLocaleString()}</span>
                </div>
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Annual savings</span>
                <span className="font-semibold text-foreground tabular-nums">${breakdown.savings.annual.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Reduction</span>
                <span className="font-semibold text-success tabular-nums">{breakdown.savings.percentage}%</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <StatBlock
              label="ROI Period"
              value={breakdown.roi.paybackPeriod}
              icon={<Clock className="w-3.5 h-3.5" />}
              color="bg-info-bg text-info"
            />
            <StatBlock
              label="3-Year Savings"
              value={`$${(breakdown.roi.totalSavings3Year / 1000).toFixed(0)}k`}
              icon={<PiggyBank className="w-3.5 h-3.5" />}
              color="bg-success-bg text-success"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
