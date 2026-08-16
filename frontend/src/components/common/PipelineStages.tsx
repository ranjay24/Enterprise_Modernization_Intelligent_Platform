import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircle, Loader2, Circle, XCircle, ChevronDown, ChevronRight,
  Clock, RotateCcw, Sparkles, FileText,
} from 'lucide-react';
import { cn } from '@/utils/cn';
import { PHASE_LABELS } from '@/utils/constants';

const allPhases = [
  'extraction',
  'static_analysis',
  'enterprise_analysis',
  'ai_boundaries',
  'ai_readiness',
  'ai_adrs',
  'ai_migration',
  'ai_cost',
  'ai_explainability',
  'results_assembly',
  'report_generation',
  'manifest',
];

const aiPhases = new Set([
  'ai_boundaries', 'ai_readiness', 'ai_adrs', 'ai_migration', 'ai_cost', 'ai_explainability',
]);

interface PipelineStagesProps {
  currentPhase: string | null;
  progress: number;
  completedPhases?: string[];
  onRetry?: (phase: string) => void;
}

const TERMINAL_PHASES = new Set(['analysis_complete', 'completed_with_errors', 'generation_complete', 'generation_with_warnings']);

export function PipelineStages({ currentPhase, progress, completedPhases, onRetry }: PipelineStagesProps) {
  const [expandedPhase, setExpandedPhase] = useState<string | null>(null);

  const phaseIdx = allPhases.indexOf(currentPhase || '');
  const showAllDone = TERMINAL_PHASES.has(currentPhase || '');
  const isFailed = currentPhase === 'failed';
  const completedCount = (completedPhases || []).filter((p) => allPhases.includes(p)).length;
  const effectiveIdx = showAllDone ? allPhases.length : Math.max(phaseIdx, completedCount);

  return (
    <div className="w-full space-y-1">
      {/* Progress summary */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-[var(--text-primary)] tabular-nums">{Math.round(progress)}%</span>
          <span className="text-xs text-[var(--text-secondary)]">
            {showAllDone ? 'All stages complete' : isFailed ? 'Failed' : `${effectiveIdx} of ${allPhases.length} stages`}
          </span>
        </div>
        {!showAllDone && !isFailed && (
          <div className="w-28 h-1.5 rounded-full bg-[var(--border-subtle)] overflow-hidden">
            <div
              className="h-full rounded-full bg-[var(--accent-blue)] transition-all duration-500 ease-[var(--ease-out)]"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>

      {/* Stage nodes */}
      <div className="relative">
        {/* Vertical connecting line */}
        <div className="absolute left-[13px] top-3 bottom-3 w-px bg-[var(--border-subtle)]" />

        <div className="space-y-2">
          {allPhases.map((phase, idx) => {
            const done = idx < effectiveIdx;
            const active = idx === effectiveIdx;
            const waiting = idx > effectiveIdx;
            const failed = isFailed && active;
            const expanded = expandedPhase === phase;

            return (
              <div key={phase} className="relative">
                <div className={cn(
                  'flex items-start gap-3 p-3 rounded-lg transition-all duration-[var(--duration-base)]',
                  active && 'bg-[var(--accent-blue)]/5 border border-[var(--accent-blue)]/15',
                  done && 'bg-[var(--success)]/5',
                  failed && 'bg-[var(--risk)]/5 border border-[var(--risk)]/15',
                  waiting && 'opacity-50'
                )}>
                  {/* Status icon */}
                  <div className="relative shrink-0 mt-0.5">
                    {done ? (
                      <CheckCircle className="w-[14px] h-[14px] text-[var(--success)]" />
                    ) : active ? (
                      <Loader2 className="w-[14px] h-[14px] text-[var(--accent-blue)] animate-spin" />
                    ) : failed ? (
                      <XCircle className="w-[14px] h-[14px] text-[var(--risk)]" />
                    ) : (
                      <Circle className="w-[14px] h-[14px] text-[var(--text-muted)]" />
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={cn(
                        'text-sm font-medium',
                        done && 'text-[var(--success)]',
                        active && 'text-[var(--accent-blue)]',
                        failed && 'text-[var(--risk)]',
                        waiting && 'text-[var(--text-secondary)]'
                      )}>
                        {PHASE_LABELS[phase] || phase}
                      </span>

                      {/* AI badge */}
                      {aiPhases.has(phase) && (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-semibold bg-[var(--accent-purple)]/10 text-[var(--accent-purple)]">
                          <Sparkles className="w-2.5 h-2.5" /> AI
                        </span>
                      )}

                      {done && (
                        <span className="text-[10px] text-[var(--text-muted)] flex items-center gap-1">
                          <Clock className="w-3 h-3" /> ~2s
                        </span>
                      )}
                    </div>

                    {/* Expand toggle */}
                    <button
                      onClick={() => setExpandedPhase(expanded ? null : phase)}
                      className="flex items-center gap-1 text-[10px] text-[var(--text-muted)] hover:text-[var(--text-secondary)] mt-1 transition-colors"
                    >
                      {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                      {expanded ? 'Hide details' : 'Show details'}
                    </button>

                    {/* Expanded details */}
                    <AnimatePresence>
                      {expanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="mt-2 space-y-2">
                            {/* Logs */}
                            <div className="rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)] p-3">
                              <pre className="text-mono text-[10px] leading-relaxed text-[var(--text-secondary)]">
                                [{phase}] Starting phase...{'\n'}
                                {done ? `✓ Phase completed successfully` : active ? 'Processing...' : 'Waiting...'}
                              </pre>
                            </div>

                            {/* Artifacts */}
                            {done && (
                              <div className="flex items-center gap-1.5 text-[10px] text-[var(--text-muted)]">
                                <FileText className="w-3 h-3" />
                                Generated: analysis_{phase}.json
                              </div>
                            )}

                            {/* Retry button */}
                            {failed && onRetry && (
                              <button
                                onClick={() => onRetry(phase)}
                                className="flex items-center gap-1 text-[10px] font-medium text-[var(--risk)] hover:text-[var(--risk)]/80 transition-colors"
                              >
                                <RotateCcw className="w-3 h-3" /> Retry stage
                              </button>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  {/* Phase indicator dot */}
                  <div
                    className="w-2 h-2 rounded-full shrink-0 mt-1.5"
                    style={{
                      backgroundColor: done ? 'var(--success)' : active ? 'var(--accent-blue)' : failed ? 'var(--risk)' : 'var(--border-subtle)',
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
