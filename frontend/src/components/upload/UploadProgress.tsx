import { CheckCircle, Loader2 } from 'lucide-react';
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

interface UploadProgressProps {
  currentPhase: string | null;
  progress: number;
}

export function UploadProgress({ currentPhase, progress }: UploadProgressProps) {
  const phaseIdx = allPhases.indexOf(currentPhase || '');
  const showAllDone = currentPhase === 'analysis_complete' || currentPhase === 'completed_with_errors';
  const effectiveIdx = showAllDone ? allPhases.length : (phaseIdx >= 0 ? phaseIdx : 0);

  return (
    <div className="w-full max-w-lg mx-auto space-y-4">
      <div className="text-center">
        <div className="text-3xl font-bold text-primary">{Math.round(progress)}%</div>
        <p className="text-sm text-muted-foreground mt-1">
          {currentPhase ? PHASE_LABELS[currentPhase] || currentPhase : 'Starting...'}
        </p>
      </div>
      <div className="w-full bg-muted rounded-full h-2">
        <div
          className="bg-primary h-2 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="space-y-2">
        {allPhases.map((phase, idx) => {
          const done = idx < effectiveIdx;
          const active = idx === effectiveIdx;
          return (
            <div
              key={phase}
              className={cn(
                'flex items-center gap-2 text-sm px-3 py-1.5 rounded-md',
                done && 'text-green-600',
                active && 'bg-primary/10 text-primary font-medium',
                !done && !active && 'text-muted-foreground'
              )}
            >
              {done ? (
                <CheckCircle className="w-4 h-4 shrink-0" />
              ) : active ? (
                <Loader2 className="w-4 h-4 shrink-0 animate-spin" />
              ) : (
                <div className="w-4 h-4 rounded-full border border-muted-foreground/30 shrink-0" />
              )}
              <span>{PHASE_LABELS[phase] || phase}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
