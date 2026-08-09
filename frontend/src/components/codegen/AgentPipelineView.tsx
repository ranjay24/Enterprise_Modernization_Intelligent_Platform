import { CheckCircle2, Loader2, RefreshCcw, ScrollText, ShieldAlert, Compass, Hammer } from 'lucide-react';
import { cn } from '@/utils/cn';

export interface AgentStep {
  id: string;
  label: string;
  icon: 'architecture' | 'planner' | 'generator' | 'review';
  status: 'pending' | 'running' | 'completed' | 'rejected';
  detail?: string;
}

const icons = {
  architecture: Compass,
  planner: ScrollText,
  generator: Hammer,
  review: ShieldAlert,
};

interface AgentPipelineViewProps {
  steps: AgentStep[];
  iteration: number;
  inProgress: boolean;
}

export function AgentPipelineView({ steps, iteration, inProgress }: AgentPipelineViewProps) {
  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <RefreshCcw className="w-4 h-4 text-[var(--accent-blue)]" />
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Agent Pipeline</h3>
        </div>
        {iteration > 0 && (
          <span className="text-[11px] text-[var(--text-muted)]">Iteration {iteration}</span>
        )}
      </div>

      <div className="space-y-2.5">
        {steps.map((step) => {
          const Icon = icons[step.icon];
          const isDone = step.status === 'completed';
          const isRejected = step.status === 'rejected';
          const isRunning = step.status === 'running';
          return (
            <div key={step.id} className="flex items-center gap-3">
              <div
                className={cn(
                  'w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-colors',
                  isDone && 'bg-[var(--success-bg)] text-[var(--success)]',
                  isRejected && 'bg-[var(--warning)]/15 text-[var(--warning)]',
                  isRunning && 'bg-[var(--info-bg)] text-[var(--accent-blue)]',
                  step.status === 'pending' && 'bg-[var(--border-subtle)]/60 text-[var(--text-muted)]'
                )}
              >
                {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : isDone ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-[var(--text-primary)]">{step.label}</p>
                {step.detail && <p className="text-[10px] text-[var(--text-muted)] truncate">{step.detail}</p>}
              </div>
              <span
                className={cn(
                  'text-[10px] font-semibold uppercase',
                  isDone && 'text-[var(--success)]',
                  isRejected && 'text-[var(--warning)]',
                  isRunning && 'text-[var(--accent-blue)]',
                  step.status === 'pending' && 'text-[var(--text-muted)]'
                )}
              >
                {step.status === 'rejected' ? 'FEEDBACK' : step.status}
              </span>
            </div>
          );
        })}
      </div>

      {inProgress && (
        <div className="mt-4 flex items-center gap-2 text-[11px] text-[var(--text-muted)]">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          Bedrock (Nova) is processing the agent loop…
        </div>
      )}
    </div>
  );
}
