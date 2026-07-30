import React from 'react';
import { CheckCircle, Loader2, AlertCircle, Clock } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/utils/cn';
import type { UploadProgressData } from '@/types/upload';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatSpeed(bytesPerSec: number): string {
  return formatBytes(bytesPerSec) + '/s';
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

interface UploadProgressCardProps {
  progress: UploadProgressData;
  onCancel?: () => void;
}

export function UploadProgressCard({ progress, onCancel }: UploadProgressCardProps) {
  const { stage, progress: pct, uploadedBytes, totalBytes, speed, estimatedRemaining, fileName } = progress;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-2xl mx-auto border rounded-xl bg-card p-6 shadow-sm"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {stage === 'uploading' ? (
            <Loader2 className="w-5 h-5 text-primary animate-spin" />
          ) : stage === 'processing' ? (
            <Loader2 className="w-5 h-5 text-primary animate-spin" />
          ) : stage === 'complete' ? (
            <CheckCircle className="w-5 h-5 text-green-600" />
          ) : stage === 'error' ? (
            <AlertCircle className="w-5 h-5 text-destructive" />
          ) : (
            <Clock className="w-5 h-5 text-muted-foreground" />
          )}
          <div>
            <p className="font-medium text-foreground text-sm">{fileName}</p>
            <p className="text-xs text-muted-foreground capitalize">{stage === 'idle' ? 'Ready' : stage}</p>
          </div>
        </div>
        {stage === 'uploading' && onCancel && (
          <button onClick={onCancel} className="text-xs text-muted-foreground hover:text-destructive transition-colors">
            Cancel
          </button>
        )}
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">{Math.round(pct)}%</span>
          {speed > 0 && <span className="text-muted-foreground">{formatSpeed(speed)}</span>}
        </div>
        <div className="w-full bg-muted rounded-full h-2">
          <motion.div
            className={cn(
              'h-2 rounded-full transition-colors',
              stage === 'error' ? 'bg-destructive' : stage === 'complete' ? 'bg-green-600' : 'bg-primary'
            )}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{formatBytes(uploadedBytes)} of {formatBytes(totalBytes)}</span>
          {estimatedRemaining > 0 && stage === 'uploading' && (
            <span>{formatTime(estimatedRemaining)} remaining</span>
          )}
        </div>
      </div>
    </motion.div>
  );
}
