import { useState } from 'react';
import { ChevronDown, ChevronUp, Brain } from 'lucide-react';
import { cn } from '@/utils/cn';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { ConfidenceBadge } from '@/components/ui/StatusBadge';
import type { ConfidenceBreakdown } from '@/types/results';

const statusColors = {
  high: 'text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-300',
  medium: 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-300',
  low: 'text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-300',
};

export function ConfidenceCenter({ data }: { data: ConfidenceBreakdown }) {
  const [expandedFactor, setExpandedFactor] = useState<string | null>(null);

  return (
    <section>
      <SectionHeader
        title="Confidence Center"
        description="AI confidence breakdown by factor"
        action={<ConfidenceBadge value={data.overall} className="text-sm" />}
      />
      <div className="bg-card rounded-xl border p-5">
        <div className="flex items-center gap-4 mb-6">
          <div className="flex items-center justify-center w-16 h-16 rounded-full bg-purple-100 dark:bg-purple-900/30">
            <Brain className="w-8 h-8 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <div className="text-3xl font-bold text-foreground">{data.overall}%</div>
            <p className="text-sm text-muted-foreground">Overall Confidence Score</p>
          </div>
          <div className="flex-1 ml-4">
            <ProgressBar value={data.overall} color="blue" className="h-3" />
          </div>
        </div>

        <div className="space-y-3">
          {data.factors.map((factor) => (
            <div key={factor.id} className="bg-muted/50 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedFactor(expandedFactor === factor.id ? null : factor.id)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-accent/50 transition-colors text-left"
              >
                <div className="flex items-center gap-3 flex-1">
                  <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', statusColors[factor.status])}>
                    {factor.status.toUpperCase()}
                  </span>
                  <span className="text-sm font-medium text-foreground">{factor.name}</span>
                  <span className="text-xs text-muted-foreground">({factor.weight}% weight)</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-bold text-foreground">{factor.score}%</span>
                  {expandedFactor === factor.id ? (
                    <ChevronUp className="w-4 h-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-muted-foreground" />
                  )}
                </div>
              </button>
              {expandedFactor === factor.id && (
                <div className="px-4 pb-4 border-t">
                  <div className="mt-3 space-y-2">
                    <p className="text-xs text-muted-foreground">{factor.description}</p>
                    <div className="flex items-center gap-2">
                      <ProgressBar value={factor.score} className="flex-1" />
                      <span className="text-xs text-muted-foreground">Score: {factor.score}/100</span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Weight: {factor.weight}% of overall confidence
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
