import React, { useState } from 'react';
import { cn } from '@/utils/cn';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { GlassCard, GlassCardContent } from '@/components/ui/GlassCard';
import { Sparkles, ChevronDown, ChevronUp, FileText, Terminal, Code2, ExternalLink } from 'lucide-react';
import type { AIRecommendation } from '@/types/dashboard';

const categoryBadge: Record<string, string> = {
  architecture: 'bg-[hsl(var(--stage-enterprise)/0.12)] text-[hsl(var(--stage-enterprise))]',
  performance: 'bg-[var(--info-bg)] text-[var(--accent-blue)]',
  security: 'bg-[var(--danger-bg)] text-[var(--risk)]',
  cost: 'bg-[var(--success-bg)] text-[var(--success)]',
  reliability: 'bg-[hsl(var(--stage-ai-readiness)/0.12)] text-[hsl(var(--stage-ai-readiness))]',
};

function MiniGauge({ score, size = 36 }: { score: number; size?: number }) {
  const radius = (size - 4) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 100);
  const color = score >= 80 ? 'var(--success)' : score >= 60 ? 'var(--warning)' : 'var(--risk)';

  return (
    <svg width={size} height={size} className="shrink-0">
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--border-subtle)" strokeWidth={3} />
      <circle
        cx={size / 2} cy={size / 2} r={radius}
        fill="none" stroke={color} strokeWidth={3}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text
        x={size / 2} y={size / 2}
        textAnchor="middle" dominantBaseline="central"
        fill="var(--text-primary)" fontSize="9" fontWeight="600" fontFamily="var(--font-mono)"
      >
        {score}
      </text>
    </svg>
  );
}

export const RecommendationCard = React.memo(function RecommendationCard({ data }: { data: AIRecommendation }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <GlassCard glow="purple">
      <GlassCardContent className="p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2 flex-wrap min-w-0">
            <div className="w-6 h-6 rounded-lg bg-[var(--accent-purple)]/10 flex items-center justify-center shrink-0">
              <Sparkles className="w-3.5 h-3.5 text-[var(--accent-purple)]" />
            </div>
            <Badge variant={data.priority === 'critical' ? 'danger' : data.priority === 'high' ? 'warning' : 'info'} size="sm">
              {data.priority.toUpperCase()}
            </Badge>
            <span className={cn('px-1.5 py-0.5 rounded text-[10px] font-semibold', categoryBadge[data.category])}>
              {data.category}
            </span>
          </div>
          <MiniGauge score={data.confidence} />
        </div>

        <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-1">{data.title}</h4>
        <p className="text-xs text-[var(--text-secondary)] leading-relaxed mb-3">{data.recommendation}</p>

        {data.evidence.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {data.evidence.slice(0, 3).map((e, i) => (
              <span key={i} className="px-1.5 py-0.5 rounded bg-[var(--border-subtle)] text-[10px] text-[var(--text-muted)]">
                {e}
              </span>
            ))}
          </div>
        )}

        {/* Expandable reasoning */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-[11px] font-medium text-[var(--accent-purple)] hover:text-[var(--accent-purple-strong)] transition-colors mb-2"
        >
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          {expanded ? 'Hide reasoning' : 'Show reasoning'}
        </button>

        {expanded && (
          <div className="mb-3 p-3 rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)] space-y-2 text-xs text-[var(--text-secondary)]">
            <p><span className="font-semibold text-[var(--text-primary)]">Business value:</span> {data.businessValue}</p>
            <p><span className="font-semibold text-[var(--text-primary)]">Technical impact:</span> {data.technicalImpact}</p>
            <div className="flex items-center gap-3 pt-1">
              <span>Effort: <span className="font-semibold text-[var(--text-primary)]">{data.effort}</span></span>
              <span>Impact: <span className={cn('font-semibold', data.impact === 'high' ? 'text-[var(--success)]' : 'text-[var(--warning)]')}>{data.impact}</span></span>
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-[var(--border-subtle)]">
          <Button variant="ghost" size="sm" className="gap-1.5 text-[11px] h-7 px-2" disabled title="Coming soon">
            <FileText className="w-3 h-3" /> Generate ADR
          </Button>
          <Button variant="ghost" size="sm" className="gap-1.5 text-[11px] h-7 px-2" disabled title="Coming soon">
            <Terminal className="w-3 h-3" /> Generate Terraform
          </Button>
          <Button variant="ghost" size="sm" className="gap-1.5 text-[11px] h-7 px-2" disabled title="Coming soon">
            <Code2 className="w-3 h-3" /> Generate Skeleton
          </Button>
          <Button variant="ghost" size="sm" className="gap-1.5 text-[11px] h-7 px-2 ml-auto" disabled title="Coming soon">
            <ExternalLink className="w-3 h-3" /> Details
          </Button>
        </div>
      </GlassCardContent>
    </GlassCard>
  );
});
