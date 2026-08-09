import { ShieldCheck, ShieldAlert, AlertTriangle, Info, ThumbsUp } from 'lucide-react';
import type { ReviewReport, ReviewFinding } from '@/types';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/utils/cn';

const severityVariant: Record<string, 'danger' | 'warning' | 'info' | 'neutral'> = {
  critical: 'danger',
  major: 'warning',
  minor: 'info',
  info: 'neutral',
};

interface ReviewPanelProps {
  report: ReviewReport | null;
}

export function ReviewPanel({ report }: ReviewPanelProps) {
  if (!report) {
    return (
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-8 text-center">
        <ShieldCheck className="w-8 h-8 text-[var(--text-muted)] mx-auto mb-2 opacity-50" />
        <p className="text-sm text-[var(--text-muted)]">No review report available yet.</p>
      </div>
    );
  }

  const findings = report.findings || [];
  const approved = report.approved;
  const criticalCount = findings.filter((f) => f.severity === 'critical' || f.severity === 'major').length;

  return (
    <div className="space-y-4">
      <div
        className={cn(
          'rounded-xl border p-4',
          approved ? 'border-[var(--success-bg)] bg-[var(--success-bg)]/30' : 'border-[var(--warning)]/30 bg-[var(--warning)]/10'
        )}
      >
        <div className="flex items-center gap-2">
          {approved ? (
            <ThumbsUp className="w-5 h-5 text-[var(--success)]" />
          ) : (
            <ShieldAlert className="w-5 h-5 text-[var(--warning)]" />
          )}
          <div className="flex-1">
            <p className={cn('text-sm font-semibold', approved ? 'text-[var(--success)]' : 'text-[var(--warning)]')}>
              {approved ? 'Review Approved' : 'Needs Work'}
            </p>
            <p className="text-[11px] text-[var(--text-muted)]">
              Iteration {report.iteration ?? 1} · Score {report.score ?? 0}/100
              {criticalCount > 0 && !approved ? ` · ${criticalCount} critical/major finding${criticalCount > 1 ? 's' : ''}` : ''}
            </p>
          </div>
          <Badge variant={approved ? 'success' : 'warning'} size="lg">
            {approved ? 'APPROVED' : 'NEEDS WORK'}
          </Badge>
        </div>
        {report.summary && <p className="mt-2 text-xs text-[var(--text-secondary)]">{report.summary}</p>}
      </div>

      {findings.length > 0 && (
        <div className="space-y-2">
          {findings.map((f) => (
            <FindingRow key={f.id || `${f.file}-${f.finding}`} finding={f} />
          ))}
        </div>
      )}
    </div>
  );
}

function FindingRow({ finding }: { finding: ReviewFinding }) {
  const variant = severityVariant[finding.severity || 'info'] || 'neutral';
  const Icon = finding.severity === 'critical' || finding.severity === 'major' ? AlertTriangle : Info;
  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-3">
      <div className="flex items-center gap-2">
        <Icon
          className={cn(
            'w-4 h-4',
            finding.severity === 'critical' && 'text-[var(--risk)]',
            finding.severity === 'major' && 'text-[var(--warning)]',
            (finding.severity === 'minor' || !finding.severity) && 'text-[var(--accent-blue)]'
          )}
        />
        <span className="text-xs font-medium text-[var(--text-primary)] flex-1">{finding.category || 'Finding'}</span>
        <Badge variant={variant} size="sm">{finding.severity || 'info'}</Badge>
      </div>
      {finding.file && <p className="mt-1 text-[10px] font-mono text-[var(--text-muted)]">{finding.file}</p>}
      {finding.finding && <p className="mt-1 text-xs text-[var(--text-secondary)]">{finding.finding}</p>}
      {finding.recommendation && (
        <p className="mt-1.5 text-[11px] text-[var(--text-muted)] border-l-2 border-[var(--border-strong)] pl-2">
          {finding.recommendation}
        </p>
      )}
    </div>
  );
}
