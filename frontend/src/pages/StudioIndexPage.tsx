import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Sparkles, ArrowRight, CheckCircle2, Clock, Loader2 } from 'lucide-react';
import { listJobs } from '@/services/jobService';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/common/EmptyState';
import { TableSkeleton } from '@/components/common/LoadingSkeleton';

const studioReadyStatuses = ['analysis_complete', 'generation_complete', 'generation_with_warnings', 'generating'];

export default function StudioIndexPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['jobs'], queryFn: listJobs, staleTime: 30000,
  });

  if (isLoading) {
    return (
      <div className="p-6 lg:p-8 max-w-[1200px] mx-auto space-y-6">
        <SkeletonHeader />
        <TableSkeleton rows={4} />
      </div>
    );
  }

  const readyJobs = (data?.jobs || []).filter((j: any) => studioReadyStatuses.includes(j.status));
  const otherJobs = (data?.jobs || []).filter((j: any) => !studioReadyStatuses.includes(j.status));

  return (
    <div className="p-6 lg:p-8 max-w-[1200px] mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[var(--accent-purple)] to-[var(--accent-blue)] flex items-center justify-center">
          <Sparkles className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="text-[var(--font-size-3xl)] font-bold tracking-tight text-[var(--text-primary)]">Modernization Studio</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            Agentic microservice code generation — pick an analyzed job to open its studio.
          </p>
        </div>
      </div>

      {readyJobs.length === 0 ? (
        <EmptyState
          icon={<Sparkles className="w-8 h-8" />}
          title="No jobs ready for code generation"
          description="Complete an analysis first, then return here to generate Spring Boot microservices."
          action={<Link to="/upload"><Button variant="primary">Analyze Codebase</Button></Link>}
        />
      ) : (
        <>
          <h2 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-widest">Ready for generation</h2>
          <div className="space-y-2">
            {readyJobs.map((job: any) => {
              const generating = job.status === 'generating';
              const done = ['generation_complete', 'generation_with_warnings'].includes(job.status);
              return (
                <div key={job.job_id} className="flex items-center gap-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
                  <div className={generating ? 'w-9 h-9 rounded-lg bg-[var(--info-bg)] flex items-center justify-center' : done ? 'w-9 h-9 rounded-lg bg-[var(--success-bg)] flex items-center justify-center' : 'w-9 h-9 rounded-lg bg-[var(--border-subtle)] flex items-center justify-center'}>
                    {generating ? <Loader2 className="w-4.5 h-4.5 text-[var(--accent-blue)] animate-spin" /> : done ? <CheckCircle2 className="w-4.5 h-4.5 text-[var(--success)]" /> : <Clock className="w-4.5 h-4.5 text-[var(--text-muted)]" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">{job.filename}</p>
                    <p className="text-[11px] text-[var(--text-muted)]">
                      Job {job.job_id.slice(0, 8)} · {new Date(job.created_at).toLocaleString()}
                    </p>
                  </div>
                  <Badge variant={generating ? 'info' : done ? 'success' : 'secondary'} size="sm" dot>
                    {generating ? 'generating' : done ? 'generation complete' : 'analysis complete'}
                  </Badge>
                  <Link to={`/jobs/${job.job_id}/studio`}>
                    <Button variant={generating ? 'outline' : 'primary'} size="sm" className="gap-1.5" disabled={generating}>
                      Open Studio <ArrowRight className="w-3.5 h-3.5" />
                    </Button>
                  </Link>
                </div>
              );
            })}
          </div>
        </>
      )}

      {otherJobs.length > 0 && (
        <>
          <h2 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-widest pt-2">Other jobs</h2>
          <div className="space-y-2">
            {otherJobs.map((job: any) => (
              <div key={job.job_id} className="flex items-center gap-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)]/50 p-4 opacity-70">
                <div className="w-9 h-9 rounded-lg bg-[var(--border-subtle)] flex items-center justify-center">
                  <Clock className="w-4.5 h-4.5 text-[var(--text-muted)]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[var(--text-primary)] truncate">{job.filename}</p>
                  <p className="text-[11px] text-[var(--text-muted)]">
                    Job {job.job_id.slice(0, 8)} · status {job.status}
                  </p>
                </div>
                <Badge variant="neutral" size="sm">{job.status}</Badge>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function SkeletonHeader() {
  return (
    <div className="flex items-center gap-3">
      <div className="w-11 h-11 rounded-xl bg-[var(--border-subtle)] animate-pulse" />
      <div className="space-y-2">
        <div className="h-5 w-48 rounded bg-[var(--border-subtle)] animate-pulse" />
        <div className="h-3 w-72 rounded bg-[var(--border-subtle)]/60 animate-pulse" />
      </div>
    </div>
  );
}
