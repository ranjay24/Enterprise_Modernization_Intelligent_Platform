import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import {
  GitBranch,
  Box,
  Database,
  Layers,
  Sparkles,
  Radio,
  Loader2,
} from 'lucide-react';
import { listJobs, getAnalysisResults, getCodeGenArchitecture, getCodeGenStatus } from '@/services/jobService';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/common/EmptyState';
import { TableSkeleton } from '@/components/common/LoadingSkeleton';
import { ArchitectureGraph, ArchitectureLegend } from '@/components/codegen/ArchitectureGraph';
import { AWSMigrationArchitecture } from '@/components/results/AWSMigrationArchitecture';
import { cn } from '@/utils/cn';
import type { JobResponse } from '@/types/api';
import type { CodeGenService, ArchitectureNode } from '@/types/codegen';

type View = 'target' | 'current';

const MIGRATION_READY_STATUSES = ['generation_complete', 'generation_with_warnings'];

export default function ArchitecturePage() {
  const navigate = useNavigate();
  const [view, setView] = useState<View>('target');
  const [selectedJobId, setSelectedJobId] = useState<string>('');

  const { data: jobsData, isLoading: jobsLoading } = useQuery({
    queryKey: ['jobs'], queryFn: listJobs, staleTime: 30000,
  });

  const codegenReadyJobs = useMemo(
    () => (jobsData?.jobs || []).filter((j: JobResponse) =>
      ['analysis_complete', 'generation_complete', 'generation_with_warnings', 'generating'].includes(j.status)
    ),
    [jobsData]
  );

  const activeJobId = selectedJobId || codegenReadyJobs[0]?.job_id;
  const activeJob = codegenReadyJobs.find((j: JobResponse) => j.job_id === activeJobId);
  const migrationReady = !!activeJob && MIGRATION_READY_STATUSES.includes(activeJob.status);

  const { data: results, isLoading: resultsLoading } = useQuery({
    queryKey: ['analysis', activeJobId],
    queryFn: () => getAnalysisResults(activeJobId!),
    enabled: !!activeJobId && view === 'current',
    staleTime: 60000,
  });

  const { data: codegenStatus } = useQuery({
    queryKey: ['codegen-status', activeJobId],
    queryFn: () => getCodeGenStatus(activeJobId!),
    enabled: !!activeJobId,
    refetchInterval: (q) => (q.state.data?.in_progress ? 3000 : false),
  });

  const { data: design, isLoading: designLoading, isError: designError } = useQuery({
    queryKey: ['codegen-architecture', activeJobId],
    queryFn: () => getCodeGenArchitecture(activeJobId!),
    enabled: !!activeJobId,
    staleTime: 30000,
  });

  const isLoading = jobsLoading || (view === 'current' ? resultsLoading : designLoading);
  const generatedServices = design?.generated_services || design?.services?.map((s: CodeGenService) => s.id) || [];

  if (isLoading && !jobsLoading && view === 'current' && !results) {
    return <div className="p-6 lg:p-8 max-w-[1440px] mx-auto"><TableSkeleton rows={5} /></div>;
  }

  return (
    <div className="p-6 lg:p-8 max-w-[1440px] mx-auto space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[var(--font-size-3xl)] font-bold tracking-tight text-[var(--text-primary)] mb-1">Architecture</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            Bedrock-generated target microservice architecture from the agent pipeline
          </p>
        </div>

        {codegenReadyJobs.length > 0 && (
          <div className="flex items-center gap-2">
            <select
              value={activeJobId}
              onChange={(e) => setSelectedJobId(e.target.value)}
              className="h-8 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] text-xs text-[var(--text-primary)] px-2.5 focus-ring"
            >
              {codegenReadyJobs.map((j: JobResponse) => (
                <option key={j.job_id} value={j.job_id}>
                  {j.filename} · {j.job_id.slice(0, 8)}
                </option>
              ))}
            </select>
            {codegenStatus?.in_progress && (
              <span className="flex items-center gap-1.5 text-xs text-[var(--accent-blue)]">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> generating
              </span>
            )}
          </div>
        )}
      </div>

      {/* View toggle */}
      <div className="flex items-center gap-1 border-b border-[var(--border-subtle)] w-fit">
        <button
          onClick={() => setView('target')}
          className={cn(
            'flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors',
            view === 'target' ? 'border-[var(--accent-purple)] text-[var(--accent-purple)]' : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)]'
          )}
        >
          <Sparkles className="w-4 h-4" /> Target (Code Generation)
        </button>
        <button
          onClick={() => setView('current')}
          className={cn(
            'flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors',
            view === 'current' ? 'border-[var(--accent-blue)] text-[var(--accent-blue)]' : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)]'
          )}
        >
          <Layers className="w-4 h-4" /> AWS Migration
        </button>
      </div>

      {view === 'target' ? (
        design ? (
          <>
            <div className="grid grid-cols-4 gap-3">
              {[
                { icon: Box, label: 'Target Services', value: design.services?.length ?? design.nodes?.filter((n: ArchitectureNode) => n.type === 'service').length ?? 0, color: 'bg-[var(--info-bg)] text-[var(--accent-blue)]' },
                { icon: Database, label: 'Databases', value: design.nodes?.filter((n: ArchitectureNode) => n.type === 'database').length ?? 0, color: 'bg-[var(--success-bg)] text-[var(--success)]' },
                { icon: Radio, label: 'Message Brokers', value: design.nodes?.filter((n: ArchitectureNode) => n.type === 'broker').length ?? 0, color: 'bg-[var(--warning-bg)] text-[var(--warning)]' },
                { icon: GitBranch, label: 'Connections', value: design.edges?.length ?? 0, color: 'bg-[var(--border-subtle)] text-[var(--text-muted)]' },
              ].map((stat) => (
                <div key={stat.label} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center', stat.color)}>
                      <stat.icon className="w-4.5 h-4.5" />
                    </div>
                    <span className="text-xs text-[var(--text-secondary)]">{stat.label}</span>
                  </div>
                  <p className="text-2xl font-bold text-[var(--text-primary)] tabular-nums">{stat.value}</p>
                </div>
              ))}
            </div>

            {codegenStatus?.summary && (
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant={codegenStatus.summary.approved ? 'success' : 'warning'} dot>
                  {codegenStatus.summary.approved ? 'Reviewer approved' : 'Review pending / regenerating'}
                </Badge>
                {codegenStatus.summary.iterations != null && (
                  <span className="text-[11px] text-[var(--text-muted)]">Iteration {codegenStatus.summary.iterations}</span>
                )}
                {generatedServices.length > 0 && (
                  <span className="text-[11px] text-[var(--text-muted)]">
                    Generated: {generatedServices.length} service{generatedServices.length > 1 ? 's' : ''}
                  </span>
                )}
              </div>
            )}

            <ArchitectureGraph
              design={design}
              height="h-[520px]"
              onSelectNode={(node: ArchitectureNode) => {
                // navigate to studio on service click
                if (activeJobId && node?.type === 'service') {
                  navigate(`/jobs/${activeJobId}/studio?tab=plan`);
                }
              }}
            />
            <ArchitectureLegend />

            {design.services && design.services.length > 0 && (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {design.services.map((svc: CodeGenService) => (
                  <div key={svc.id} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-[var(--text-primary)]">{svc.name || svc.id}</span>
                      {svc.broker_role && svc.broker_role !== 'none' && (
                        <Badge variant="info" size="sm">{svc.broker_role}</Badge>
                      )}
                    </div>
                    <p className="text-[10px] text-[var(--text-muted)] mb-2">{svc.business_capability}</p>
                    {svc.broker_rationale && (
                      <p className="text-[10px] text-[var(--text-muted)] border-l-2 border-[var(--border-strong)] pl-2">
                        {svc.broker_rationale}
                      </p>
                    )}
                    {svc.resilience && svc.resilience.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {svc.resilience.map((r: string) => (
                          <span key={r} className="px-1.5 py-0.5 rounded bg-[var(--border-subtle)]/60 text-[9px] text-[var(--text-muted)]">{r}</span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {activeJobId && (
              <div className="flex justify-center">
                <Link to={`/jobs/${activeJobId}/studio`}>
                  <Button variant="outline" className="gap-2"><Sparkles className="w-4 h-4" /> Open Modernization Studio</Button>
                </Link>
              </div>
            )}
          </>
        ) : designError || (codegenReadyJobs.length > 0 && !design && !designLoading && !codegenStatus?.in_progress) ? (
          <EmptyState
            icon={<Sparkles className="w-8 h-8" />}
            title="No target architecture yet"
            description="Run the agentic code generation pipeline to produce the target microservice architecture. Start it from the Modernization Studio."
            action={activeJobId ? (
              <Link to={`/jobs/${activeJobId}/studio`}><Button className="gap-2"><Sparkles className="w-4 h-4" /> Open Modernization Studio</Button></Link>
            ) : undefined}
          />
        ) : (
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
              <TableSkeleton rows={3} />
            </div>
          </div>
        )
      ) : results ? (
        migrationReady ? (
          <AWSMigrationArchitecture key={activeJobId} waves={results.migration_waves} services={results.service_boundaries} />
        ) : (
          <EmptyState
            icon={<Layers className="w-8 h-8" />}
            title="Generate microservices first"
            description="AWS migration details are produced after the microservices are generated. Start code generation from the Modernization Studio."
            action={activeJobId ? (
              <Link to={`/jobs/${activeJobId}/studio`}><Button className="gap-2"><Sparkles className="w-4 h-4" /> Generate Microservices</Button></Link>
            ) : undefined}
          />
        )
      ) : (
        <EmptyState
          icon={<GitBranch className="w-8 h-8" />}
          title="No migration data"
          description="Run an analysis to generate the AWS migration architecture blueprint."
          action={<Link to="/upload"><Button variant="primary">Analyze Codebase</Button></Link>}
        />
      )}
    </div>
  );
}

