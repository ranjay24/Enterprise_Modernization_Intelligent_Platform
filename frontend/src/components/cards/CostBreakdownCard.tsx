import React from 'react';
import { cn } from '@/utils/cn';
import type { CostBreakdownData } from '@/types/dashboard';

function formatUSD(n: number): string {
  return '$' + n.toLocaleString();
}

const categories = ['compute', 'storage', 'networking', 'operations', 'licensing'] as const;

export const CostBreakdownCard = React.memo(function CostBreakdownCard({ data }: { data: CostBreakdownData }) {
  return (
    <article className="bg-card rounded-xl border p-5">
      <h3 className="font-semibold text-foreground text-sm mb-4">Cost Breakdown</h3>
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3">
          <p className="text-xs text-red-600 dark:text-red-400 font-medium">Current Monthly</p>
          <p className="text-xl font-bold text-foreground">{formatUSD(data.current.monthly)}</p>
        </div>
        <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
          <p className="text-xs text-green-600 dark:text-green-400 font-medium">Projected Monthly</p>
          <p className="text-xl font-bold text-foreground">{formatUSD(data.projected.monthly)}</p>
        </div>
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
          <p className="text-xs text-blue-600 dark:text-blue-400 font-medium">Monthly Savings</p>
          <p className="text-xl font-bold text-foreground">{formatUSD(data.savings.monthly)}</p>
        </div>
      </div>
      <div className="space-y-2">
        {categories.map((cat) => {
          const current = data.current.breakdown[cat];
          const projected = data.projected.breakdown[cat];
          const maxVal = Math.max(current, projected);
          return (
            <div key={cat} className="text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="text-muted-foreground capitalize">{cat}</span>
                <span className="text-muted-foreground">{formatUSD(current)} → {formatUSD(projected)}</span>
              </div>
              <div className="flex gap-1 h-2">
                <div className="bg-red-300 dark:bg-red-700 rounded" style={{ width: `${(current / maxVal) * 100}%` }} />
                <div className="bg-green-300 dark:bg-green-700 rounded" style={{ width: `${(projected / maxVal) * 100}%` }} />
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-4 pt-3 border-t grid grid-cols-3 gap-2 text-xs">
        <div><span className="text-muted-foreground">Payback:</span> <span className="font-medium">{data.roi.paybackPeriod}</span></div>
        <div><span className="text-muted-foreground">Break-even:</span> <span className="font-medium">Month {data.roi.breakEvenMonths}</span></div>
        <div><span className="text-muted-foreground">3-Year Savings:</span> <span className="font-medium text-green-600">{formatUSD(data.roi.totalSavings3Year)}</span></div>
      </div>
    </article>
  );
});
