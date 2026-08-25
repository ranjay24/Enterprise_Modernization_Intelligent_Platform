import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { ConfidenceBadge } from '@/components/ui/StatusBadge';
import type { ExplainabilityEntry } from '@/types/dashboard';

export const ExplainabilityCard = React.memo(function ExplainabilityCard({
  data,
  expanded: controlledExpanded,
  onToggle,
}: {
  data: ExplainabilityEntry;
  expanded?: boolean;
  onToggle?: () => void;
}) {
  const [internalExpanded, setInternalExpanded] = useState(false);
  const expanded = controlledExpanded ?? internalExpanded;
  const toggle = onToggle || (() => setInternalExpanded(!internalExpanded));

  return (
    <article className="bg-card rounded-xl border overflow-hidden">
      <button onClick={toggle} className="w-full px-5 py-4 flex items-center justify-between hover:bg-accent/50 transition-colors text-left">
        <div>
          <h3 className="font-semibold text-foreground text-sm">{data.service}</h3>
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{data.primaryReason}</p>
        </div>
        <div className="flex items-center gap-2">
          <ConfidenceBadge value={data.confidence} />
          {expanded ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
        </div>
      </button>
      {expanded && (
        <div className="px-5 pb-5 space-y-4 border-t">
          <div className="mt-3">
            <h4 className="text-xs font-semibold text-foreground mb-1">Why?</h4>
            <p className="text-xs text-muted-foreground">{data.primaryReason}</p>
            {data.secondaryReasons.length > 0 && (
              <ul className="text-xs text-muted-foreground mt-1 space-y-0.5">
                {data.secondaryReasons.map((r, i) => <li key={i}>• {r}</li>)}
              </ul>
            )}
          </div>
          <div>
            <h4 className="text-xs font-semibold text-foreground mb-2">Evidence</h4>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(data.evidence).map(([key, val]) => (
                <div key={key} className="bg-muted rounded-lg p-2">
                  <div className="text-xs font-medium text-foreground capitalize">{key.replace(/([A-Z])/g, ' $1')}</div>
                  <div className="text-xs text-muted-foreground">{val}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="text-xs font-semibold text-green-700 dark:text-green-400 mb-1">Pros</h4>
              <ul className="text-xs text-muted-foreground space-y-0.5">
                {data.tradeoffs.pros.map((p, i) => <li key={i}>+ {p}</li>)}
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-red-700 dark:text-red-400 mb-1">Cons</h4>
              <ul className="text-xs text-muted-foreground space-y-0.5">
                {data.tradeoffs.cons.map((c, i) => <li key={i}>- {c}</li>)}
              </ul>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div><span className="text-muted-foreground">Business:</span> <span className="text-foreground">{data.impact.business}</span></div>
            <div><span className="text-muted-foreground">Technical:</span> <span className="text-foreground">{data.impact.technical}</span></div>
            <div><span className="text-muted-foreground">Risk:</span> <span className="text-foreground">{data.impact.risk}</span></div>
          </div>
        </div>
      )}
    </article>
  );
});
