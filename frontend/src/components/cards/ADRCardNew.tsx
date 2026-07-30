import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Badge } from '@/components/ui/Badge';
import { ConfidenceBadge, StatusBadge } from '@/components/ui/StatusBadge';
import type { ADRPreview } from '@/types/dashboard';

export const ADRCardNew = React.memo(function ADRCardNew({ data }: { data: ADRPreview }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <article className="bg-card rounded-xl border overflow-hidden hover:shadow-md transition-all">
      <button onClick={() => setExpanded(!expanded)} className="w-full px-5 py-4 flex items-center justify-between hover:bg-accent/50 transition-colors text-left">
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono bg-muted px-2 py-1 rounded">{data.id}</span>
          <div>
            <h3 className="font-semibold text-foreground text-sm">{data.title}</h3>
            <p className="text-xs text-muted-foreground">Service: {data.service}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={data.status} />
          <ConfidenceBadge value={data.confidence} />
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>
      {expanded && (
        <div className="px-5 pb-5 space-y-4 border-t">
          <div className="mt-3">
            <h4 className="text-xs font-semibold text-foreground mb-1">Context</h4>
            <p className="text-xs text-muted-foreground whitespace-pre-wrap">{data.context}</p>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-foreground mb-1">Decision</h4>
            <p className="text-xs text-muted-foreground whitespace-pre-wrap">{data.decision}</p>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div>
              <h4 className="text-xs font-semibold text-green-700 dark:text-green-400 mb-1">Positive</h4>
              <ul className="text-xs text-muted-foreground space-y-0.5">
                {data.consequences.positive.map((p, i) => <li key={i}>+ {p}</li>)}
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-red-700 dark:text-red-400 mb-1">Negative</h4>
              <ul className="text-xs text-muted-foreground space-y-0.5">
                {data.consequences.negative.map((n, i) => <li key={i}>- {n}</li>)}
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-yellow-700 dark:text-yellow-400 mb-1">Risks</h4>
              <ul className="text-xs text-muted-foreground space-y-0.5">
                {data.consequences.risks.map((r, i) => <li key={i}>⚠ {r}</li>)}
              </ul>
            </div>
          </div>
          {data.alternatives.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-foreground mb-1">Alternatives Considered</h4>
              <div className="flex flex-wrap gap-1.5">
                {data.alternatives.map((a, i) => (
                  <Badge key={i} variant="outline" className="text-xs">{a}</Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </article>
  );
});
