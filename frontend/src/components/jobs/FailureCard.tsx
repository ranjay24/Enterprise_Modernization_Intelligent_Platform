import React from 'react';
import { XCircle, RotateCcw, Download, Clock, AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/Button';
import type { JobDetail } from '@/types/jobs';

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

interface FailureCardProps {
  job: JobDetail;
  onRetry?: (jobId: string) => void;
}

export function FailureCard({ job, onRetry }: FailureCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="border border-destructive/30 rounded-xl bg-destructive/5 p-4"
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center shrink-0">
          <XCircle className="w-5 h-5 text-destructive" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-medium text-foreground truncate">{job.projectName}</h4>
            <span className="text-xs text-destructive bg-destructive/10 px-2 py-0.5 rounded-full">Failed</span>
          </div>
          <p className="text-sm text-muted-foreground mb-2 line-clamp-2">{job.failureReason}</p>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Failed at: {job.failedStage?.replace(/_/g, ' ')}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatElapsed(job.elapsed)}
            </span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 mt-3 ml-13">
        {onRetry && (
          <Button variant="outline" size="sm" onClick={() => onRetry(job.id)}>
            <RotateCcw className="w-3.5 h-3.5 mr-1" />
            Retry
          </Button>
        )}
        <Button variant="ghost" size="sm" className="text-muted-foreground">
          <Download className="w-3.5 h-3.5 mr-1" />
          Download Logs
        </Button>
      </div>
    </motion.div>
  );
}
