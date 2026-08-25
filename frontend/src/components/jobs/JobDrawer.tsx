import React, { useEffect } from 'react';
import { X, FileArchive, User, Tag, Building2, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { StageBadge } from './StageBadge';
import { PipelineTimeline } from './PipelineTimeline';
import type { JobDetail } from '@/types/jobs';
import { formatDate } from '@/utils/formatters';

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

interface JobDrawerProps {
  job: JobDetail | null;
  open: boolean;
  onClose: () => void;
}

export function JobDrawer({ job, open, onClose }: JobDrawerProps) {
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && job && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
            onClick={onClose}
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-card border-l z-50 overflow-y-auto"
          >
            <div className="sticky top-0 bg-card border-b p-4 flex items-center justify-between z-10">
              <div className="min-w-0">
                <h2 className="font-semibold text-foreground truncate">{job.projectName}</h2>
                <p className="text-xs text-muted-foreground font-mono">{job.id}</p>
              </div>
              <button onClick={onClose} className="p-2 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              <div className="flex items-center gap-3">
                <StageBadge status={job.status} size="md" />
                <span className="text-sm text-muted-foreground">{job.currentTask}</span>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-foreground mb-3">Pipeline Progress</h3>
                <div className="overflow-x-auto">
                  <PipelineTimeline completedStages={job.stagesCompleted} currentStage={job.currentStage} />
                </div>
                <div className="mt-2 text-center text-sm text-muted-foreground">
                  {Math.round(job.progress)}% complete &middot; {job.stagesCompleted.length}/12 stages
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-foreground mb-3">Project Metadata</h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="bg-muted/50 rounded-lg p-3">
                    <p className="text-xs text-muted-foreground flex items-center gap-1"><FileArchive className="w-3 h-3" /> File</p>
                    <p className="font-medium text-foreground mt-0.5">{job.fileName}</p>
                    <p className="text-xs text-muted-foreground">{formatBytes(job.fileSize)}</p>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-3">
                    <p className="text-xs text-muted-foreground flex items-center gap-1"><Tag className="w-3 h-3" /> Version</p>
                    <p className="font-medium text-foreground mt-0.5">{job.metadata.version}</p>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-3">
                    <p className="text-xs text-muted-foreground flex items-center gap-1"><Building2 className="w-3 h-3" /> Domain</p>
                    <p className="font-medium text-foreground mt-0.5">{job.metadata.businessDomain || '—'}</p>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-3">
                    <p className="text-xs text-muted-foreground flex items-center gap-1"><User className="w-3 h-3" /> Owner</p>
                    <p className="font-medium text-foreground mt-0.5 truncate">{job.metadata.owner || '—'}</p>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-foreground mb-3">Execution Timeline</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Started</span>
                    <span className="font-medium text-foreground">{formatDate(job.startedAt)}</span>
                  </div>
                  {job.completedAt && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Completed</span>
                      <span className="font-medium text-foreground">{formatDate(job.completedAt)}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Elapsed</span>
                    <span className="font-medium text-foreground">{formatElapsed(job.elapsed)}</span>
                  </div>
                  {job.estimatedRemaining > 0 && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Est. Remaining</span>
                      <span className="font-medium text-foreground">{formatElapsed(job.estimatedRemaining)}</span>
                    </div>
                  )}
                </div>
              </div>

              {job.status === 'completed' && (
                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-3">Analysis Results</h3>
                  <div className="grid grid-cols-2 gap-3">
                    {job.architectureScore !== null && (
                      <div className="bg-muted/50 rounded-lg p-3 text-center">
                        <p className="text-2xl font-bold text-foreground">{job.architectureScore}</p>
                        <p className="text-xs text-muted-foreground">Architecture Score</p>
                      </div>
                    )}
                    {job.aiConfidence !== null && (
                      <div className="bg-muted/50 rounded-lg p-3 text-center">
                        <p className="text-2xl font-bold text-foreground">{job.aiConfidence}%</p>
                        <p className="text-xs text-muted-foreground">AI Confidence</p>
                      </div>
                    )}
                    {job.readinessScore !== null && (
                      <div className="bg-muted/50 rounded-lg p-3 text-center">
                        <p className="text-2xl font-bold text-foreground">{job.readinessScore}</p>
                        <p className="text-xs text-muted-foreground">Readiness Score</p>
                      </div>
                    )}
                    {job.servicesCount !== null && (
                      <div className="bg-muted/50 rounded-lg p-3 text-center">
                        <p className="text-2xl font-bold text-foreground">{job.servicesCount}</p>
                        <p className="text-xs text-muted-foreground">Services Found</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                {job.status === 'completed' && (
                  <Button onClick={() => { onClose(); navigate(`/jobs/${job.id}/results`); }} className="flex-1">
                    <ExternalLink className="w-4 h-4 mr-1" />
                    View Results
                  </Button>
                )}
                {job.status === 'failed' && (
                  <Button variant="outline" className="flex-1" disabled title="Coming soon">
                    Retry Analysis
                  </Button>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
