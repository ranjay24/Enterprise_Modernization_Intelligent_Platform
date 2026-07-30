import React from 'react';
import { Upload, Play, CheckCircle, Brain, FileText, AlertTriangle, Trophy, Clock } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/utils/cn';
import type { ActivityEvent } from '@/types/jobs';
import { formatDate } from '@/utils/formatters';

const eventIcons: Record<string, React.ElementType> = {
  upload: Upload,
  analysis_start: Play,
  stage_complete: CheckCircle,
  ai_complete: Brain,
  adr_generated: FileText,
  report_generated: Trophy,
  failed: AlertTriangle,
};

const eventColors: Record<string, string> = {
  upload: 'text-blue-600 bg-blue-100 dark:bg-blue-900/30',
  analysis_start: 'text-primary bg-primary/10',
  stage_complete: 'text-green-600 bg-green-100 dark:bg-green-900/30',
  ai_complete: 'text-purple-600 bg-purple-100 dark:bg-purple-900/30',
  adr_generated: 'text-amber-600 bg-amber-100 dark:bg-amber-900/30',
  report_generated: 'text-green-600 bg-green-100 dark:bg-green-900/30',
  failed: 'text-destructive bg-destructive/10',
};

interface ActivityTimelineProps {
  events: ActivityEvent[];
}

export function ActivityTimeline({ events }: ActivityTimelineProps) {
  return (
    <div className="space-y-0">
      {events.map((event, i) => {
        const Icon = eventIcons[event.type] || Clock;
        const colorClass = eventColors[event.type] || 'text-muted-foreground bg-muted';

        return (
          <motion.div
            key={event.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="flex items-start gap-3 relative"
          >
            {/* Connector line */}
            {i < events.length - 1 && (
              <div className="absolute left-[15px] top-8 w-px h-full bg-muted-foreground/20" />
            )}
            <div className={cn('w-8 h-8 rounded-full flex items-center justify-center shrink-0 relative z-10', colorClass)}>
              <Icon className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0 pb-4">
              <p className="text-sm font-medium text-foreground">{event.projectName}</p>
              <p className="text-xs text-muted-foreground">{event.message}</p>
              <p className="text-[10px] text-muted-foreground mt-0.5 flex items-center gap-1">
                <Clock className="w-2.5 h-2.5" />
                {formatDate(event.timestamp)}
              </p>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
