import React from 'react';
import { Eye, Pause, Play, XCircle, Clock, Loader2, Brain } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/Button';
import { StageBadge } from './StageBadge';
import type { JobDetail } from '@/types/jobs';

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function formatBytes(bytes: number): string {
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

interface ActiveJobCardProps {
  job: JobDetail;
  onViewDetails: (job: JobDetail) => void;
  onPause?: (jobId: string) => void;
  onResume?: (jobId: string) => void;
  onCancel?: (jobId: string) => void;
}

export function ActiveJobCard({ job, onViewDetails, onPause, onResume, onCancel }: ActiveJobCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="border rounded-xl bg-card p-5 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-foreground truncate">{job.projectName}</h3>
            <StageBadge status={job.status} />
          </div>
          <p className="text-xs text-muted-foreground font-mono">{job.fileName} &middot; {formatBytes(job.fileSize)}</p>
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="text-muted-foreground">{job.currentTask}</span>
            <span className="font-medium text-foreground">{Math.round(job.progress)}%</span>
          </div>
          <div className="w-full bg-muted rounded-full h-2">
            <motion.div
              className="bg-primary h-2 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${job.progress}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" /> {formatElapsed(job.elapsed)}
          </span>
          <span className="flex items-center gap-1">
            <Loader2 className="w-3 h-3" /> ~{formatElapsed(job.estimatedRemaining)} left
          </span>
          <span className="flex items-center gap-1">
            <Brain className="w-3 h-3" /> {job.stagesCompleted.length}/12 stages
          </span>
        </div>

        <div className="flex items-center gap-2 pt-1">
          <Button variant="outline" size="sm" onClick={() => onViewDetails(job)}>
            <Eye className="w-3.5 h-3.5 mr-1" />
            Details
          </Button>
          {job.status === 'paused' ? (
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground"
              onClick={() => onResume?.(job.id)}
            >
              <Play className="w-3.5 h-3.5 mr-1" />
              Resume
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground"
              onClick={() => onPause?.(job.id)}
            >
              <Pause className="w-3.5 h-3.5 mr-1" />
              Pause
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive hover:text-destructive"
            onClick={() => onCancel?.(job.id)}
          >
            <XCircle className="w-3.5 h-3.5 mr-1" />
            Cancel
          </Button>
        </div>
      </div>
    </motion.div>
  );
}
