import React from 'react';
import { Upload, Search, GitBranch, Brain, FileText, Check, Loader2, Circle } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/utils/cn';
import type { WorkflowStep } from '@/types/upload';

const iconMap: Record<string, React.ElementType> = { Upload, Search, GitBranch, Brain, FileText };

interface WorkflowTimelineProps {
  steps: WorkflowStep[];
  activeStep?: number;
}

export function WorkflowTimeline({ steps, activeStep }: WorkflowTimelineProps) {
  return (
    <div className="w-full">
      <h3 className="text-sm font-semibold text-foreground mb-4">How It Works</h3>
      <div className="flex flex-col sm:flex-row items-stretch gap-0 sm:gap-0">
        {steps.map((step, i) => {
          const Icon = iconMap[step.icon] || Circle;
          const isActive = activeStep === step.step;
          const isComplete = activeStep !== undefined && step.step < activeStep;
          const isPending = activeStep === undefined || step.step > activeStep;
          const isLast = i === steps.length - 1;

          return (
            <React.Fragment key={step.id}>
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className={cn(
                  'flex-1 flex flex-col items-center text-center p-4 rounded-xl transition-colors relative',
                  isActive && 'bg-primary/10 border border-primary/20',
                  isComplete && 'bg-green-50 dark:bg-green-900/10',
                  isPending && 'bg-muted/30'
                )}
              >
                <div className={cn(
                  'w-10 h-10 rounded-full flex items-center justify-center mb-2',
                  isActive && 'bg-primary text-primary-foreground',
                  isComplete && 'bg-green-600 text-white',
                  isPending && 'bg-muted text-muted-foreground'
                )}>
                  {isComplete ? (
                    <Check className="w-5 h-5" />
                  ) : isActive ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Icon className="w-5 h-5" />
                  )}
                </div>
                <p className={cn(
                  'text-sm font-medium',
                  isActive && 'text-primary',
                  isComplete && 'text-green-700 dark:text-green-400',
                  isPending && 'text-muted-foreground'
                )}>
                  {step.title}
                </p>
                <p className="text-xs text-muted-foreground mt-1 hidden sm:block">{step.description}</p>
                <span className={cn(
                  'absolute -top-1 -right-1 w-5 h-5 rounded-full text-[10px] font-bold flex items-center justify-center',
                  isActive && 'bg-primary text-primary-foreground',
                  isComplete && 'bg-green-600 text-white',
                  isPending && 'bg-muted text-muted-foreground'
                )}>
                  {step.step}
                </span>
              </motion.div>
              {!isLast && (
                <div className="hidden sm:flex items-center justify-center w-6 shrink-0">
                  <div className={cn(
                    'w-px h-full min-h-[2px]',
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
