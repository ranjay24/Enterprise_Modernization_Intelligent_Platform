import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Sparkles,
  Play,
  RefreshCw,
  LayoutGrid,
  FileCode2,
  ShieldAlert,
  ListChecks,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Boxes,
} from 'lucide-react';
import {
  startCodeGeneration,
  getCodeGenStatus,
  getCodeGenArchitecture,
  getCodeGenPlan,
  getCodeGenCode,
  getCodeGenReview,
  getJobStatus,
} from '@/services/jobService';
import type { CodeGenStatus, ArchitectureDesign, CodeGenPlan, CodeGenCodeResponse, ReviewReport } from '@/types';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/common/LoadingSkeleton';
import { AgentPipelineView, type AgentStep } from '@/components/codegen/AgentPipelineView';
import { ArchitectureGraph, ArchitectureLegend } from '@/components/codegen/ArchitectureGraph';
import { CodeExplorer } from '@/components/codegen/CodeExplorer';
import { ReviewPanel } from '@/components/codegen/ReviewPanel';
import { cn } from '@/utils/cn';

const POLL_MS = 2500;

type Tab = 'pipeline' | 'architecture' | 'plan' | 'code' | 'review';

const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: 'pipeline', label: 'Pipeline', icon: Boxes },
  { id: 'architecture', label: 'Architecture', icon: LayoutGrid },
  { id: 'plan', label: 'Plan', icon: ListChecks },
  { id: 'code', label: 'Code', icon: FileCode2 },
  { id: 'review', label: 'Review', icon: ShieldAlert },
];

function buildAgentSteps(
  status: CodeGenStatus | undefined,
  design: ArchitectureDesign | undefined,
  review: ReviewReport | null | undefined
): AgentStep[] {
  const summary = status?.summary;
  const inProgress = status?.in_progress ?? false;
  const stage = status?.current_stage ?? '';
  const approved = !!summary?.approved || !!review?.approved;
  const generatedCount = status?.services_generated?.length ?? 0;
  const designDone = !!design;

  const isArchRunning = stage === 'architecture_design';
  const isPlanRunning = stage === 'service_planning';
  const isGenRunning = stage === 'code_generation' || stage.startsWith('code_generation_');
  const isReviewRunning = stage === 'review';
  const loopFinished = !!summary || stage === 'finalize';

  const plannerDone = designDone && (inProgress || loopFinished);
  const reviewRejected = !!review && !review.approved && (inProgress || loopFinished);

  return [
    {
      id: 'architecture',
      label: 'Architecture Designer',
      icon: 'architecture',
      detail: design ? `${design.services?.length ?? 0} services, Kafka/RabbitMQ classified` : 'Detects services & broker roles',
      status: isArchRunning ? 'running' : designDone || loopFinished ? 'completed' : 'pending',
    },
    {
      id: 'planner',
      label: 'Service Planner',
      icon: 'planner',
      detail: 'Wave-based plan, resilience & Feign clients',
      status: isPlanRunning ? 'running' : plannerDone ? 'completed' : 'pending',
    },
    {
      id: 'generator',
      label: 'Code Generator',
      icon: 'generator',
      detail: `Spring Boot 3 + Java 17 services · ${generatedCount} done`,
      status: isGenRunning ? 'running' : generatedCount > 0 || loopFinished ? 'completed' : 'pending',
    },
    {
      id: 'review',
      label: 'Review Agent',
      icon: 'review',
      detail: reviewRejected ? 'Rejected — feeding back to Planner' : approved ? 'Approved' : 'Validates compilation & consistency',
      status: reviewRejected ? 'rejected' : approved ? 'completed' : isReviewRunning ? 'running' : 'pending',
    },
  ];
}

export default function ModernizationStudioPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>('pipeline');
  const [selectedService, setSelectedService] = useState<string>('');

  const jobQuery = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const st = q.state.data?.status;
      return st === 'generating' ? POLL_MS : false;
    },
  });

  const statusQuery = useQuery({
    queryKey: ['codegen-status', jobId],
    queryFn: () => getCodeGenStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => (q.state.data?.in_progress ? POLL_MS : false),
  });

  const architectureQuery = useQuery({
    queryKey: ['codegen-architecture', jobId],
    queryFn: () => getCodeGenArchitecture(jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => (q.state.data ? false : POLL_MS),
  });

  const planQuery = useQuery({
    queryKey: ['codegen-plan', jobId],
    queryFn: () => getCodeGenPlan(jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => (q.state.data ? false : POLL_MS),
  });

  const codeQuery = useQuery({
    queryKey: ['codegen-code', jobId, selectedService],
    queryFn: () => getCodeGenCode(jobId!, selectedService || undefined),
    enabled: !!jobId && activeTab === 'code',
  });

  const reviewQuery = useQuery({
    queryKey: ['codegen-review', jobId],
    queryFn: () => getCodeGenReview(jobId!),
    enabled: !!jobId && (activeTab === 'review' || activeTab === 'pipeline'),
  });

  const startMutation = useMutation({
    mutationFn: () => startCodeGeneration(jobId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job', jobId] });
      queryClient.invalidateQueries({ queryKey: ['codegen-status', jobId] });
      setActiveTab('pipeline');
    },
  });

  const status = statusQuery.data;
  const job = jobQuery.data;
  const design = architectureQuery.data;
  const plan = planQuery.data;
  const codeData = codeQuery.data;
  const review = reviewQuery.data;

  const canStart =
    !!job && ['analysis_complete', 'generation_complete', 'generation_with_warnings'].includes(job.status);
  const isGenerating = status?.in_progress || job?.status === 'generating';
  const isDone = status?.summary?.status === 'generation_complete' || status?.summary?.status === 'generation_with_warnings' || job?.status === 'generation_complete';

  useEffect(() => {
    if (status?.services_generated?.length && !selectedService) {
      setSelectedService(status.services_generated[0]);
    }
  }, [status?.services_generated, selectedService]);

  const steps = useMemo(() => buildAgentSteps(status, design, review), [status, design, review]);

  const renderTab = () => {
    switch (activeTab) {
      case 'architecture':
        return (
          <div className="space-y-3">
            <ArchitectureGraph design={design || {}} />
            <ArchitectureLegend />
            {design?.services?.length ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {design.services.map((svc) => (
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
                        {svc.resilience.map((r) => (
                          <span key={r} className="px-1.5 py-0.5 rounded bg-[var(--border-subtle)]/60 text-[9px] text-[var(--text-muted)]">{r}</span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              !architectureQuery.isLoading && <p className="text-sm text-[var(--text-muted)] text-center py-8">Architecture not generated yet.</p>
            )}
          </div>
        );
      case 'plan':
        return <PlanView plan={plan} isLoading={planQuery.isLoading} />;
      case 'code':
        return (
          <div className="space-y-3">
            {codeData && Object.keys(codeData.services).length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                {Object.keys(codeData.services).map((sid) => (
                  <button
                    key={sid}
                    onClick={() => setSelectedService(sid)}
                    className={cn(
                      'px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors',
                      selectedService === sid
                        ? 'border-[var(--accent-blue)] bg-[var(--accent-blue)]/10 text-[var(--accent-blue)]'
                        : 'border-[var(--border-subtle)] bg-[var(--bg-card)] text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                    )}
                  >
                    {sid}
                  </button>
                ))}
              </div>
            )}
            {selectedService && codeData?.services[selectedService] ? (
              <CodeExplorer code={codeData.services[selectedService]} />
            ) : (
              <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-8 text-center">
                <FileCode2 className="w-8 h-8 text-[var(--text-muted)] mx-auto mb-2 opacity-50" />
                <p className="text-sm text-[var(--text-muted)]">No service code generated yet. Start the pipeline first.</p>
              </div>
            )}
          </div>
        );
      case 'review':
        return <ReviewPanel report={review || null} />;
      case 'pipeline':
      default:
        return (
          <div className="space-y-4">
            <AgentPipelineView steps={steps} iteration={status?.summary?.iterations ?? 0} inProgress={isGenerating} />
            {status?.summary?.services_generated && status.summary.services_generated.length > 0 && (
              <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
                <p className="text-xs font-semibold text-[var(--text-primary)] mb-2">Generated services</p>
                <div className="flex flex-wrap gap-2">
                  {status.summary.services_generated.map((s) => (
                    <button
                      key={s}
                      onClick={() => { setSelectedService(s); setActiveTab('code'); }}
                      className="px-2.5 py-1 rounded-lg bg-[var(--success-bg)]/50 text-[var(--success)] text-xs font-medium hover:bg-[var(--success-bg)] transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-[1440px] mx-auto space-y-6">
      <div className="flex items-center justify-between gap-4">
        <Link
          to={`/jobs/${jobId}/results`}
          onClick={() => queryClient.invalidateQueries({ queryKey: ['jobs'] })}
          className="inline-flex items-center gap-1.5 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors w-fit"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Results
        </Link>
        {job?.status === 'generating' && (
          <Badge variant="info" dot><Loader2 className="w-3 h-3 animate-spin mr-1" /> Generating</Badge>
        )}
      </div>

      {/* Hero */}
      <div className="rounded-xl border border-[var(--border-subtle)] bg-gradient-to-r from-[var(--bg-card)] to-[var(--accent-blue)]/5 p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[var(--accent-purple)] to-[var(--accent-blue)] flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <Badge variant="premium" size="lg">Modernization Studio</Badge>
            </div>
            <h1 className="text-[var(--font-size-2xl)] font-bold tracking-tight text-[var(--text-primary)]">
              Agentic Microservice Code Generation
            </h1>
            <p className="text-sm text-[var(--text-secondary)] mt-1 max-w-2xl">
              Four Bedrock agents (Architecture Designer → Planner → Code Generator → Reviewer) turn the analyzed monolith into
              Spring Boot 3 + Java 17 microservices with Kafka/RabbitMQ messaging and Resilience4j.
            </p>
          </div>

          <div className="flex flex-col items-end gap-2">
            {canStart && !isGenerating && (
              <Button
                onClick={() => startMutation.mutate()}
                disabled={startMutation.isPending}
                className="gap-2"
              >
                {startMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {isDone ? 'Regenerate' : 'Start Code Generation'}
              </Button>
            )}
            {isGenerating && (
              <div className="flex items-center gap-2 text-xs text-[var(--accent-blue)]">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                Pipeline running · {status?.progress ?? 0}%
              </div>
            )}
            {status?.summary?.approved === false && !isGenerating && (
              <Badge variant="warning" dot>Review pending — findings fed back to Planner</Badge>
            )}
            {isDone && (
              <Badge variant="success" dot><CheckCircle2 className="w-3 h-3 mr-1" /> Generation Complete</Badge>
            )}
          </div>
        </div>

        {status?.current_stage && status.current_stage !== 'idle' && (
          <div className="mt-4">
            <div className="h-1.5 rounded-full bg-[var(--border-subtle)] overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-[var(--accent-blue)] to-[var(--accent-purple)] transition-all duration-700"
                style={{ width: `${status.progress ?? 0}%` }}
              />
            </div>
            <p className="mt-1.5 text-[10px] text-[var(--text-muted)] capitalize">Stage: {status.current_stage}</p>
          </div>
        )}
      </div>

      {startMutation.isError && (
        <div className="flex items-center gap-2 rounded-xl border border-[var(--danger-bg)] bg-[var(--danger-bg)]/20 p-3 text-sm text-[var(--risk)]">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {startMutation.error?.message || 'Failed to start code generation'}
        </div>
      )}

      {!canStart && !isGenerating && job && (
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-6 text-center">
          <AlertCircle className="w-8 h-8 text-[var(--warning)] mx-auto mb-2" />
          <p className="text-sm text-[var(--text-secondary)]">
            Code generation requires a completed analysis. Current job status: <strong>{job.status}</strong>.
          </p>
          <Link to={`/jobs/${jobId}/results`}>
            <Button variant="outline" className="mt-3 gap-2"><ArrowLeft className="w-4 h-4" /> View Analysis Results</Button>
          </Link>
        </div>
      )}

      {(canStart || isGenerating || isDone || status?.summary) && (
        <>
          <div className="flex items-center gap-1 border-b border-[var(--border-subtle)] overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px whitespace-nowrap transition-colors',
                  activeTab === tab.id
                    ? 'border-[var(--accent-blue)] text-[var(--accent-blue)]'
                    : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                )}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
                {tab.id === 'review' && review && <Badge size="sm" variant={review.approved ? 'success' : 'warning'}>{review.approved ? 'OK' : '!'}</Badge>}
                {tab.id === 'code' && status && (
                  <span className="text-[10px] text-[var(--text-muted)]">({status.services_generated?.length ?? 0})</span>
                )}
              </button>
            ))}
          </div>

          <div className="min-h-[400px]">
            {(isGenerating && activeTab === 'architecture' && !architectureQuery.data) ||
            (isGenerating && activeTab === 'plan' && !planQuery.data) ||
            (isGenerating && activeTab === 'code' && !codeData) ? (
              <div className="space-y-3">
                <Skeleton className="h-[520px] w-full rounded-xl" />
              </div>
            ) : (
              renderTab()
            )}
          </div>
        </>
      )}
    </div>
  );
}

function PlanView({ plan, isLoading }: { plan: CodeGenPlan | null | undefined; isLoading: boolean }) {
  if (isLoading) return <Skeleton className="h-[400px] w-full rounded-xl" />;
  if (!plan) {
    return (
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-8 text-center">
        <ListChecks className="w-8 h-8 text-[var(--text-muted)] mx-auto mb-2 opacity-50" />
        <p className="text-sm text-[var(--text-muted)]">No generation plan yet.</p>
      </div>
    );
  }

  const services = Array.isArray(plan.services) ? plan.services : Object.values(plan.services || {});

  return (
    <div className="space-y-4">
      {plan.waves && plan.waves.length > 0 && (
        <div className="grid gap-3">
          {plan.waves.map((wave) => (
            <div key={wave.wave ?? wave.name} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
              <div className="flex items-center gap-2 mb-2">
                <Badge variant="secondary">Wave {wave.wave ?? '?'}</Badge>
                <span className="text-xs font-semibold text-[var(--text-primary)]">{wave.name}</span>
              </div>
              {wave.rationale && <p className="text-[10px] text-[var(--text-muted)] mb-2">{wave.rationale}</p>}
              <div className="flex flex-wrap gap-1.5">
                {wave.services?.map((s) => (
                  <span key={s} className="px-2 py-0.5 rounded-md bg-[var(--border-subtle)]/60 text-[11px] text-[var(--text-secondary)]">{s}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {services.length > 0 && (
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] overflow-hidden">
          <div className="px-4 py-3 border-b border-[var(--border-subtle)]">
            <p className="text-xs font-semibold text-[var(--text-primary)]">Service Plans</p>
          </div>
          <div className="divide-y divide-[var(--border-subtle)]">
            {services.map((svc: any) => (
              <div key={svc.id} className="px-4 py-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-[var(--text-primary)]">{svc.name || svc.id}</span>
                  {svc.broker_role && <Badge variant="info" size="sm">{svc.broker_role}</Badge>}
                </div>
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-[var(--text-muted)]">
                  {svc.server_port && <span>port {svc.server_port}</span>}
                  {svc.business_capability && <span>{svc.business_capability}</span>}
                  {svc.source_classes?.length && <span>{svc.source_classes.length} source classes</span>}
                  {svc.exposed_endpoints?.length && <span>{svc.exposed_endpoints.length} REST endpoints</span>}
                  {svc.events?.subscribes?.length && <span>{svc.events.subscribes.length} subscriptions</span>}
                  {svc.events?.publishes?.length && <span>{svc.events.publishes.length} publications</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {plan.global_config && Object.keys(plan.global_config).length > 0 && (
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
          <p className="text-xs font-semibold text-[var(--text-primary)] mb-2">Global Config</p>
          <pre className="text-[11px] text-[var(--text-muted)] whitespace-pre-wrap">{JSON.stringify(plan.global_config, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
