import React from 'react';
import { Upload, CheckCircle, Search, GitBranch, Building2, Puzzle, Layers, Brain, FileText, Route, BarChart3, Trophy, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/utils/cn';
import { PIPELINE_STAGES } from '@/types/jobs';

const iconMap: Record<string, React.ElementType> = {
  Upload, CheckCircle, Search, GitBranch, Building2, Puzzle, Layers, Brain, FileText, Route, BarChart3, Trophy,
};

interface PipelineTimelineProps {
  completedStages: string[];
  currentStage: string;
}

export function PipelineTimeline({ completedStages, currentStage }: PipelineTimelineProps) {
  const currentIdx = PIPELINE_STAGES.findIndex((s) => s.key === currentStage);

  return (
    <div className="w-full overflow-x-auto pb-2">
      <div className="flex items-start gap-0 min-w-max">
        {PIPELINE_STAGES.map((stage, i) => {
          const isComplete = completedStages.includes(stage.key);
          const isCurrent = stage.key === currentStage;
          const isPending = !isComplete && !isCurrent;
          const Icon = iconMap[stage.icon] || CheckCircle;
          const isLast = i === PIPELINE_STAGES.length - 1;

          return (
            <React.Fragment key={stage.id}>
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.04 }}
                className="flex flex-col items-center text-center w-20 shrink-0"
              >
                <div className={cn(
                  'w-10 h-10 rounded-full flex items-center justify-center mb-1.5 transition-all',
                  isComplete && 'bg-green-600 text-white',
                  isCurrent && 'bg-primary text-primary-foreground ring-2 ring-primary/30 ring-offset-2 ring-offset-background',
                  isPending && 'bg-muted text-muted-foreground'
                )}>
                  {isComplete ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : isCurrent ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Icon className="w-5 h-5" />
                  )}
                </div>
                <p className={cn(
                  'text-[10px] font-medium leading-tight',
                  isComplete && 'text-green-600 dark:text-green-400',
                  isCurrent && 'text-primary font-semibold',
                  isPending && 'text-muted-foreground'
                )}>
                  {stage.label}
                </p>
              </motion.div>
              {!isLast && (
                <div className="flex items-center justify-center w-6 shrink-0 mt-3">
                  <div className={cn(
                    'w-full h-0.5',
                    i < currentIdx || (currentIdx >= 0 && i < currentIdx) ? 'bg-green-400' :
                    isComplete ? 'bg-green-400' : 'bg-muted-foreground/20'
                  )} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
