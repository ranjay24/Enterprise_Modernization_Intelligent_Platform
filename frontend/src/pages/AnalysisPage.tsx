import { useParams, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowLeft, ArrowRight, Clock, CheckCircle2 } from 'lucide-react';
import { useJobPolling } from '@/hooks/useJobPolling';
import { PipelineStages } from '@/components/common/PipelineStages';
import { GlassCard, GlassCardContent, GlassCardHeader, GlassCardTitle } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/common/LoadingSkeleton';
import { Link } from 'react-router-dom';

export default function AnalysisPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { data: job, isLoading, error, isError } = useJobPolling(jobId);

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4">
        <Skeleton className="h-6 w-48 mx-auto mb-2 rounded-lg" />
        <Skeleton className="h-4 w-64 mx-auto mb-8 rounded-lg" />
        <Skeleton className="h-96 w-full rounded-xl" />
      </div>
    );
  }

  if (isError || !job) {
    return (
      <div className="max-w-md mx-auto text-center py-20 px-4">
        <div className="w-14 h-14 rounded-2xl bg-[var(--danger-bg)] flex items-center justify-center mx-auto mb-5">
          <AlertCircle className="w-7 h-7 text-[var(--risk)]" />
        </div>
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-1">Unable to load analysis</h2>
        <p className="text-sm text-[var(--text-secondary)] mb-6">{error?.message || 'Job not found'}</p>
        <div className="flex items-center justify-center gap-3">
          <Button variant="outline" onClick={() => navigate('/jobs')} className="gap-2">
            <ArrowLeft className="w-4 h-4" />
            Back to Jobs
          </Button>
          <Button onClick={() => navigate('/upload')} className="gap-2">
            Try Again
            <ArrowRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    );
  }

  const isComplete = job.status === 'analysis_complete';
  const isFailed = job.status === 'failed';

  return (
    <div className="max-w-2xl mx-auto py-12 px-4 space-y-8">
      {/* Header */}
      <div className="text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium mb-3"
          style={{
            backgroundColor: isComplete ? 'var(--success-bg)' : isFailed ? 'var(--danger-bg)' : 'var(--info-bg)',
            color: isComplete ? 'var(--success)' : isFailed ? 'var(--risk)' : 'var(--accent-blue)',
          }}
        >
          {isComplete ? (
            <><CheckCircle2 className="w-3.5 h-3.5" /> Analysis Complete</>
          ) : isFailed ? (
            <><AlertCircle className="w-3.5 h-3.5" /> Analysis Failed</>
          ) : (
            <><Clock className="w-3.5 h-3.5 animate-pulse-soft" /> In Progress</>
          )}
        </div>
        <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-1">{job.filename}</h2>
        <p className="text-sm text-[var(--text-secondary)]">
          Job {job.job_id?.slice(0, 8)}...
          {job.progress > 0 && <span className="ml-2 tabular-nums">{job.progress}%</span>}
        </p>
      </div>

      {/* Pipeline stages — GitHub Actions style */}
      <GlassCard glow="blue">
        <GlassCardHeader>
          <GlassCardTitle>Pipeline Progress</GlassCardTitle>
        </GlassCardHeader>
        <GlassCardContent>
          <PipelineStages currentPhase={job.current_phase} progress={job.progress} completedPhases={job.completed_phases} />
        </GlassCardContent>
      </GlassCard>

      {/* Completed state */}
      {isComplete && (
        <div className="text-center">
          <Link to={`/jobs/${jobId}/results`}>
            <Button variant="primary" size="lg" className="gap-2">
              View Results
              <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
}
