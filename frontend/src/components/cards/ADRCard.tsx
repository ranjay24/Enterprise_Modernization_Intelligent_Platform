import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { formatConfidence } from '@/utils/formatters';
import type { ADR } from '@/types';

export function ADRCard({ adr }: { adr: ADR }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-card border rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-accent/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono bg-muted px-2 py-1 rounded">{adr.id}</span>
          <span className="font-medium text-card-foreground">{adr.title}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">Confidence: {formatConfidence(adr.confidence)}%</span>
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>
      {expanded && (
        <div className="px-6 pb-6 space-y-4 border-t">
          <div className="mt-4">
            <h4 className="text-sm font-semibold mb-1">Context</h4>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">{adr.context}</p>
          </div>
          <div>
            <h4 className="text-sm font-semibold mb-1">Decision</h4>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">{adr.decision}</p>
          </div>
          {adr.tradeoffs && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="text-sm font-semibold text-green-700 dark:text-green-400 mb-1">Pros</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  {(adr.tradeoffs.pros || []).map((p, i) => (
                    <li key={i}>+ {p}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-red-700 dark:text-red-400 mb-1">Cons</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  {(adr.tradeoffs.cons || []).map((c, i) => (
                    <li key={i}>- {c}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
          {adr.migration_impact && (
            <div className="bg-primary/5 border border-primary/20 rounded-lg p-4">
              <h4 className="text-sm font-semibold mb-2">Migration Impact</h4>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Complexity:</span>
                  <span className="ml-2 font-medium">{adr.migration_impact.complexity}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Effort:</span>
                  <span className="ml-2 font-medium">{adr.migration_impact.estimated_effort}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Team:</span>
                  <span className="ml-2 font-medium">{adr.migration_impact.team_size} engineers</span>
                </div>
              </div>
              {adr.migration_impact.risk_factors && adr.migration_impact.risk_factors.length > 0 && (
                <div className="mt-2">
                  <span className="text-muted-foreground text-sm">Risk factors:</span>
                  <ul className="text-sm mt-1">
                    {adr.migration_impact.risk_factors.map((rf, i) => (
                      <li key={i}>• {rf}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
