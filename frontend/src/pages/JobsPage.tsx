import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Upload, FolderOpen, Loader2, CheckCircle, XCircle, Clock, Brain, Percent, LayoutDashboard, FileText, GitBranch, Trash2, Play, BarChart3 } from 'lucide-react';
import { cn } from '@/utils/cn';
import { listJobs, pauseJob, resumeJob, cancelJob, deleteAllJobs } from '@/services/jobService';
import { Button } from '@/components/ui/Button';
import { SummaryCard } from '@/components/jobs/SummaryCard';
import { ActiveJobCard } from '@/components/jobs/ActiveJobCard';
import { PipelineTimeline } from '@/components/jobs/PipelineTimeline';
import { CompletedTable } from '@/components/jobs/CompletedTable';
import { FailureCard } from '@/components/jobs/FailureCard';
import { ActivityTimeline } from '@/components/jobs/ActivityTimeline';
import { JobDrawer } from '@/components/jobs/JobDrawer';
import { JobFilters } from '@/components/jobs/JobFilters';
import { EmptyState } from '@/components/common/EmptyState';
import { TableSkeleton } from '@/components/common/LoadingSkeleton';
import { useAppStore } from '@/store/useAppStore';
import { mockJobSummary, mockActiveJobs, mockCompletedJobs, mockFailedJobs, mockQueuedJobs, mockActivityEvents } from '@/data/mockJobs';
import type { JobDetail, JobExtendedStatus } from '@/types/jobs';
import type { JobResponse } from '@/types';

type FilterStatus = 'all' | JobExtendedStatus;

const BACKEND_PHASE_ORDER = [
  'extraction', 'static_analysis', 'enterprise_analysis', 'ai_boundaries',
  'ai_readiness', 'ai_adrs', 'ai_migration', 'ai_cost', 'ai_explainability',
  'results_assembly', 'report_generation', 'manifest',
];

function apiJobToDetail(job: JobResponse): JobDetail {
  const statusMap: Record<string, JobExtendedStatus> = {
    uploaded: 'uploading',
    analyzing: 'analyzing',
    paused: 'paused',
    cancelled: 'cancelled',
    analysis_complete: 'completed',
    failed: 'failed',
    deployed: 'completed',
  };

  const currentPhase = job.current_phase || '';
  const phaseIdx = BACKEND_PHASE_ORDER.indexOf(currentPhase);

  let completedStages: string[];
  let currentStage: string;
  if (job.completed_phases && job.completed_phases.length > 0) {
    completedStages = job.completed_phases;
    currentStage = phaseIdx >= 0 ? currentPhase : BACKEND_PHASE_ORDER[Math.max(0, job.completed_phases.length)];
  } else if (job.status === 'analysis_complete') {
    completedStages = [...BACKEND_PHASE_ORDER];
    currentStage = 'report_generation';
  } else if (phaseIdx >= 0) {
    completedStages = BACKEND_PHASE_ORDER.slice(0, phaseIdx);
    currentStage = currentPhase;
  } else {
    completedStages = [];
    currentStage = BACKEND_PHASE_ORDER[0];
  }

  let currentTask: string;
  if (job.status === 'analyzing') {
    currentTask = currentPhase ? `Running ${currentPhase}...` : 'Starting analysis...';
  } else if (job.status === 'analysis_complete') {
    currentTask = 'Analysis complete';
  } else if (job.status === 'paused') {
    currentTask = currentPhase ? `Paused at ${currentPhase}` : 'Paused';
  } else if (job.status === 'cancelled') {
    currentTask = 'Cancelled by user';
  } else if (job.status === 'failed') {
    currentTask = job.error || 'Analysis failed';
  } else {
    currentTask = 'Waiting...';
  }

  return {
    id: job.job_id,
    projectName: job.filename.replace(/\.zip$/i, '').replace(/[-_]/g, ' '),
    fileName: job.filename,
    fileSize: job.file_size || 0,
    version: '1.0.0',
    status: statusMap[job.status] || 'queued',
    currentStage,
    progress: job.progress,
    startedAt: job.created_at,
    completedAt: job.status === 'analysis_complete' ? job.updated_at : null,
    elapsed: job.status === 'analysis_complete'
      ? Math.round((new Date(job.updated_at).getTime() - new Date(job.created_at).getTime()) / 1000)
      : Math.round((Date.now() - new Date(job.created_at).getTime()) / 1000),
    estimatedRemaining: job.status === 'analysis_complete' ? 0 : 300,
    currentTask,
    architectureScore: null,
    aiConfidence: null,
    readinessScore: null,
    riskLevel: null,
    servicesCount: null,
    failureReason: job.error || (job.status === 'cancelled' ? 'Cancelled by user' : null),
    failedStage: job.status === 'failed' ? job.current_phase : null,
    stagesCompleted: completedStages,
    metadata: { projectName: job.filename, version: '1.0.0', description: '', businessDomain: '', teamName: '', owner: '' },
  };
}

export default function JobsPage() {
  const { demoMode } = useAppStore();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all');
  const [drawerJob, setDrawerJob] = useState<JobDetail | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const { data: apiData, isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: listJobs,
    staleTime: 6000,
    refetchInterval: 3000,
  });

  const pauseMutation = useMutation({
    mutationFn: pauseJob,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  });

  const cancelMutation = useMutation({
    mutationFn: cancelJob,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  });

  const resumeMutation = useMutation({
    mutationFn: resumeJob,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  });

  const deleteAllMutation = useMutation({
    mutationFn: deleteAllJobs,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
  });

  const allDemoJobs = useMemo(() => [...mockQueuedJobs, ...mockActiveJobs, ...mockCompletedJobs, ...mockFailedJobs], []);

  const allJobs = useMemo(() => {
    if (demoMode) return allDemoJobs;
    return (apiData?.jobs || []).map(apiJobToDetail);
  }, [demoMode, apiData, allDemoJobs]);

  const filteredJobs = useMemo(() => {
    let filtered = allJobs;
    if (search) {
      const q = search.toLowerCase();
      filtered = filtered.filter((j) => j.projectName.toLowerCase().includes(q) || j.fileName.toLowerCase().includes(q));
    }
    if (statusFilter !== 'all') {
      filtered = filtered.filter((j) => j.status === statusFilter);
    }
    return filtered;
  }, [allJobs, search, statusFilter]);

  const activeJobs = useMemo(() => filteredJobs.filter((j) => ['queued', 'uploading', 'validating', 'analyzing', 'ai_processing', 'generating_report', 'paused'].includes(j.status)), [filteredJobs]);
  const completedJobs = useMemo(() => filteredJobs.filter((j) => j.status === 'completed'), [filteredJobs]);
  const failedJobs = useMemo(() => filteredJobs.filter((j) => j.status === 'failed'), [filteredJobs]);

  const summary = useMemo(() => {
    if (demoMode) return mockJobSummary;
    return {
      totalProjects: allJobs.length,
      queuedJobs: allJobs.filter((j) => j.status === 'queued').length,
      runningJobs: activeJobs.length,
      completedJobs: completedJobs.length,
      failedJobs: failedJobs.length,
      avgAnalysisTime: completedJobs.length > 0 ? Math.round(completedJobs.reduce((a, j) => a + j.elapsed, 0) / completedJobs.length) : 0,
      avgConfidence: 0,
      successRate: allJobs.length > 0 ? Math.round((completedJobs.length / allJobs.length) * 100) : 0,
    };
  }, [demoMode, allJobs, activeJobs, completedJobs, failedJobs]);

  const openDrawer = (job: JobDetail) => { setDrawerJob(job); setDrawerOpen(true); };
  const closeDrawer = () => { setDrawerOpen(false); setTimeout(() => setDrawerJob(null), 300); };

  const handlePause = (jobId: string) => { pauseMutation.mutate(jobId); };
  const handleResume = (jobId: string) => { resumeMutation.mutate(jobId); };
  const handleCancel = (jobId: string) => {
    if (window.confirm('Cancel this job permanently?')) cancelMutation.mutate(jobId);
  };
  const handleDeleteAll = () => {
    if (window.confirm('Delete ALL jobs and data? This cannot be undone.')) deleteAllMutation.mutate();
  };

  if (isLoading && !demoMode) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto">
        <h1 className="text-display text-foreground mb-6">Jobs</h1>
        <TableSkeleton rows={5} />
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-10">
      {/* ── Header ── */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-display text-foreground mb-1">Jobs</h1>
          <p className="text-body-sm text-muted-foreground">Monitor and manage all modernization assessment jobs</p>
        </div>
        <Link to="/upload">
          <Button variant="primary" className="gap-2">
            <Upload className="w-4 h-4" />
            New Analysis
          </Button>
        </Link>
      </div>

      {/* ── Summary cards ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryCard icon={FolderOpen} label="Total Projects" value={summary.totalProjects} color="bg-info-bg text-info" />
        <SummaryCard icon={Clock} label="Queued" value={summary.queuedJobs} color="bg-muted text-muted-foreground" />
        <SummaryCard icon={Loader2} label="Running" value={summary.runningJobs} color="bg-info-bg text-info" />
        <SummaryCard icon={CheckCircle} label="Completed" value={summary.completedJobs} color="bg-success-bg text-success" />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryCard icon={XCircle} label="Failed" value={summary.failedJobs} color="bg-danger-bg text-danger" />
        <SummaryCard icon={Clock} label="Avg. Time" value={`${summary.avgAnalysisTime}s`} color="bg-warning-bg text-warning" />
        <SummaryCard icon={Brain} label="Avg. Confidence" value={`${summary.avgConfidence}%`} color="bg-[hsl(var(--stage-ai-boundaries)/0.1)] text-[hsl(var(--stage-ai-boundaries))]" />
        <SummaryCard icon={Percent} label="Success Rate" value={`${summary.successRate}%`} color="bg-success-bg text-success" />
      </div>

      {/* ── Filters ── */}
      <JobFilters search={search} onSearchChange={setSearch} statusFilter={statusFilter} onStatusFilterChange={setStatusFilter} />

      {/* ── Content ── */}
      {allJobs.length === 0 && !isLoading ? (
        <EmptyState
          icon={<FolderOpen className="w-8 h-8" />}
          title="No jobs yet"
          description="Upload a codebase to get started with modernization analysis."
          action={<Link to="/upload"><Button variant="primary">Upload Codebase</Button></Link>}
        />
      ) : (
        <div className="space-y-10">
          {/* Active jobs */}
          {activeJobs.length > 0 && (
            <section>
              <h2 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-info animate-pulse-soft" />
                Running Jobs ({activeJobs.length})
              </h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                {activeJobs.map((job) => (
                  <ActiveJobCard key={job.id} job={job} onViewDetails={openDrawer} onPause={handlePause} onResume={handleResume} onCancel={handleCancel} />
                ))}
              </div>
            </section>
          )}

          {/* Pipeline overview for active jobs */}
          {activeJobs.length > 0 && (
            <section>
              <h2 className="text-base font-semibold text-foreground mb-4">Pipeline Overview</h2>
              <div className="space-y-3">
                {activeJobs.map((job) => (
                  <div key={job.id} className="border rounded-xl bg-card p-4">
                    <p className="text-sm font-medium text-foreground mb-3">{job.projectName}</p>
                    <PipelineTimeline completedStages={job.stagesCompleted} currentStage={job.currentStage} />
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Completed jobs */}
          {completedJobs.length > 0 && (
            <section>
              <h2 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-success" />
                Completed ({completedJobs.length})
              </h2>
              <CompletedTable jobs={completedJobs} />
            </section>
          )}

          {/* Failed jobs */}
          {failedJobs.length > 0 && (
            <section>
              <h2 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
                <XCircle className="w-4 h-4 text-danger" />
                Failed ({failedJobs.length})
              </h2>
              <div className="space-y-2">
                {failedJobs.map((job) => (
                  <FailureCard key={job.id} job={job} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {/* ── Demo mode activity ── */}
      {demoMode && (
        <section>
          <h2 className="text-base font-semibold text-foreground mb-4">Recent Activity</h2>
          <div className="border rounded-xl bg-card p-5">
            <ActivityTimeline events={mockActivityEvents} />
          </div>
        </section>
      )}

      {/* ── Quick actions ── */}
      <section>
        <h2 className="text-base font-semibold text-foreground mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {[
            { icon: Upload, label: 'Upload Project', href: '/upload', color: 'bg-info-bg text-info' },
            { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard', color: 'bg-primary/8 text-primary' },
            { icon: BarChart3, label: 'Reports', href: '/reports', color: 'bg-warning-bg text-warning' },
            { icon: GitBranch, label: 'Architecture', href: '/architecture', color: 'bg-[hsl(var(--stage-ai-boundaries)/0.1)] text-[hsl(var(--stage-ai-boundaries))]' },
          ].map((action) => (
            <Link
              key={action.href}
              to={action.href}
              className="flex items-center gap-3 p-3 rounded-xl border bg-card hover:bg-accent/50 transition-colors group"
            >
              <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', action.color)}>
                <action.icon className="w-4 h-4" />
              </div>
              <span className="text-sm font-medium text-foreground">{action.label}</span>
            </Link>
          ))}
          {!demoMode && (
            <button
              onClick={handleDeleteAll}
              disabled={deleteAllMutation.isPending}
              className="flex items-center gap-3 p-3 rounded-xl border bg-card hover:bg-danger-bg transition-colors text-danger group"
            >
              <div className="w-8 h-8 rounded-lg bg-danger-bg flex items-center justify-center">
                <Trash2 className="w-4 h-4" />
              </div>
              <span className="text-sm font-medium">{deleteAllMutation.isPending ? 'Deleting...' : 'Delete All'}</span>
            </button>
          )}
        </div>
      </section>

      <JobDrawer job={drawerJob} open={drawerOpen} onClose={closeDrawer} />
    </div>
  );
}


