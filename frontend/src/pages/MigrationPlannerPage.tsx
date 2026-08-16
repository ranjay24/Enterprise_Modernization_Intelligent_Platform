import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Layers, Route, Cloud, X, CheckCircle2, Sparkles, Box,
  FileSearch, GitBranch, Code2, Rocket, ShieldCheck, RefreshCcw, ThumbsUp, Bot,
  Zap, Database, Radio, Activity, Package, Lock,
  type LucideIcon,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { RiskBadge } from '@/components/cards';
import { EmptyState } from '@/components/common/EmptyState';
import { TableSkeleton } from '@/components/common/LoadingSkeleton';
import { CompletedJobSelector } from '@/components/common/CompletedJobSelector';
import { useCompletedJobs } from '@/hooks/useCompletedJobs';
import { GlassCard, GlassCardContent, GlassCardHeader, GlassCardTitle } from '@/components/ui/GlassCard';
import { cn } from '@/utils/cn';
import { buildAwsInventory, type AwsCategory } from '@/utils/awsInventory';
import type { MigrationWave } from '@/types/api';

const CATS: Record<AwsCategory, { color: string; icon: LucideIcon }> = {
  gateway: { color: 'var(--accent-purple)', icon: Route },
  compute: { color: 'var(--accent-blue)', icon: Zap },
  database: { color: 'var(--analytics)', icon: Database },
  messaging: { color: 'var(--warning)', icon: Radio },
  observability: { color: 'var(--success)', icon: Activity },
  storage: { color: 'var(--warning)', icon: Package },
  security: { color: 'var(--risk)', icon: Lock },
  other: { color: 'var(--text-secondary)', icon: Cloud },
};

interface PlannerWave extends MigrationWave {
  id?: string;
  status?: string;
  progress?: number;
  justification?: string[];
}

const MIGRATION_READY_STATUSES = ['generation_complete', 'generation_with_warnings'];

interface PipelinePhase {
  step: number;
  name: string;
  icon: LucideIcon;
  color: string;
  tagline: string;
  whatNovaDoes: string[];
  inputs: string[];
  outputs: string[];
}

const PIPELINE: PipelinePhase[] = [
  {
    step: 1,
    name: 'Analyze',
    icon: FileSearch,
    color: 'var(--accent-purple)',
    tagline: 'Bedrock Nova scans the source codebase',
    whatNovaDoes: [
      'Parses the uploaded codebase and builds a class/package inventory',
      'Constructs the service dependency graph and detects circular dependencies',
      'Scores modernization readiness per service (code, architecture, cloud, DB)',
    ],
    inputs: ['Uploaded source archive', 'Static analysis metrics'],
    outputs: ['Codebase inventory', 'Dependency graph', 'Readiness scores'],
  },
  {
    step: 2,
    name: 'Decompose',
    icon: GitBranch,
    color: 'var(--accent-blue)',
    tagline: 'Nova splits the monolith into microservices',
    whatNovaDoes: [
      'Groups classes into service boundaries using cohesion/coupling signals',
      'Generates Architecture Decision Records (ADRs) for every split',
      'Identifies the god classes and ordering required for decomposition',
    ],
    inputs: ['Codebase inventory', 'Dependency graph'],
    outputs: ['Service boundaries', 'ADRs', 'Business capability map'],
  },
  {
    step: 3,
    name: 'Generate',
    icon: Code2,
    color: 'var(--success)',
    tagline: 'Nova generates production-ready service code',
    whatNovaDoes: [
      'Scaffolds each microservice with routes, domain logic, and data access',
      'Generates API contracts, unit tests, and Dockerfile packaging',
      'Writes event contracts for inter-service communication',
    ],
    inputs: ['Service boundaries', 'ADRs', 'AWS recommendations'],
    outputs: ['Microservice source', 'API contracts', 'Tests & Dockerfiles'],
  },
  {
    step: 4,
    name: 'Provision',
    icon: Rocket,
    color: 'var(--warning)',
    tagline: 'Nova provisions the AWS target architecture',
    whatNovaDoes: [
      'Creates compute (Lambda / ECS Fargate) and data stores (RDS, DynamoDB)',
      'Wires API Gateway, SNS/SQS, and observability (CloudWatch)',
      'Applies least-privilege IAM roles and security best practices',
    ],
    inputs: ['Microservice source', 'AWS recommendations'],
    outputs: ['Infrastructure as Code', 'Deployed AWS resources', 'IAM & security config'],
  },
  {
    step: 5,
    name: 'Validate',
    icon: ShieldCheck,
    color: 'var(--success)',
    tagline: 'Nova verifies every deployed service',
    whatNovaDoes: [
      'Runs generated test suites and integration checks on the live stack',
      'Validates endpoints, data integrity, and event flows',
      'Confirms rollback readiness before each wave is accepted',
    ],
    inputs: ['Deployed AWS resources', 'Generated tests'],
    outputs: ['Validation report', 'Health checks', 'Rollback readiness'],
  },
  {
    step: 6,
    name: 'Rollback',
    icon: RefreshCcw,
    color: 'var(--risk)',
    tagline: 'Nova auto-reverts any failing change',
    whatNovaDoes: [
      'Continuously monitors for regressions and drift',
      'Automatically reverts to the last known-good state on failure',
      'Keeps an audit trail of every migration attempt',
    ],
    inputs: ['Deployed stack', 'Health checks'],
    outputs: ['Rollback playbook', 'Audit log', 'Safe-point snapshots'],
  },
];

type PlanStatus = 'review' | 'approved' | 'changes';

export default function MigrationPlannerPage() {
  const { completedJobs, selectedJobId, setSelectedJobId, selectedJob, results, isLoading, demoMode } = useCompletedJobs();

  const [selectedWave, setSelectedWave] = useState<PlannerWave | null>(null);
  const [planStatus, setPlanStatus] = useState<PlanStatus>('review');

  const totalServices = useMemo(
    () => new Set((results?.migration_waves || []).flatMap((w) => w.services ?? [])).size,
    [results]
  );
  const totalAwsServices = useMemo(
    () => new Set(
      (results?.migration_waves || []).flatMap((w) =>
        Object.values(w.aws_services_map ?? {}).flatMap((targets) => targets)
      )
    ).size,
    [results]
  );
  const awsInventory = useMemo(() => buildAwsInventory(results?.migration_waves || []), [results]);

  if (isLoading) return <div className="p-6 lg:p-8 max-w-[1440px] mx-auto"><TableSkeleton rows={5} /></div>;

  if (!results) {
    return (
      <div className="p-6 lg:p-8 max-w-[1440px] mx-auto">
        <h1 className="text-[var(--font-size-3xl)] font-bold tracking-tight text-[var(--text-primary)] mb-1">AI Migration Blueprint</h1>
        <p className="text-sm text-[var(--text-secondary)] mb-8">Autonomous migration plan generated by Amazon Bedrock Nova</p>
        <EmptyState
          icon={<Route className="w-8 h-8" />}
          title="No migration plan"
          description="Run an analysis to generate an AI-powered migration blueprint."
          action={<Link to="/upload"><Button variant="primary">Analyze Codebase</Button></Link>}
        />
      </div>
    );
  }

  const migrationReady = demoMode || (!!selectedJob && MIGRATION_READY_STATUSES.includes(selectedJob.status));
  if (!migrationReady) {
    return (
      <div className="p-6 lg:p-8 max-w-[1440px] mx-auto">
        <h1 className="text-[var(--font-size-3xl)] font-bold tracking-tight text-[var(--text-primary)] mb-1">AI Migration Blueprint</h1>
        <p className="text-sm text-[var(--text-secondary)] mb-8">Autonomous migration plan generated by Amazon Bedrock Nova</p>
        <EmptyState
          icon={<Route className="w-8 h-8" />}
          title="Generate microservices first"
          description="The AWS migration plan is produced after the microservices are generated. Start code generation to unlock the migration blueprint."
          action={selectedJob ? (
            <Link to={`/jobs/${selectedJob.job_id}/studio`}><Button className="gap-2"><Sparkles className="w-4 h-4" /> Generate Microservices</Button></Link>
          ) : (
            <Link to="/upload"><Button variant="primary">Analyze Codebase</Button></Link>
          )}
        />
      </div>
    );
  }

  const waves = (results.migration_waves || []) as PlannerWave[];
  const cost = results.cost_comparison;

  return (
    <div className="p-6 lg:p-8 max-w-[1440px] mx-auto space-y-8">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-[var(--font-size-3xl)] font-bold tracking-tight text-[var(--text-primary)] mb-1">AI Migration Blueprint</h1>
          <p className="text-sm text-[var(--text-secondary)]">Autonomous migration plan generated and executed by Amazon Bedrock Nova</p>
        </div>
        <CompletedJobSelector
          jobs={completedJobs}
          selectedJobId={selectedJobId}
          onChange={setSelectedJobId}
        />
      </div>

      {/* Approval panel */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className={cn(
          'rounded-xl border p-5',
          planStatus === 'approved'
            ? 'border-[var(--success)]/30 bg-[var(--success-bg)]/40'
            : 'border-[var(--accent-purple)]/30 bg-gradient-to-r from-[var(--accent-purple)]/8 to-[var(--bg-card)]'
        )}
      >
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="flex items-start gap-3">
            <div className={cn(
              'w-10 h-10 rounded-xl flex items-center justify-center shrink-0',
              planStatus === 'approved' ? 'bg-[var(--success)]/10' : 'bg-[var(--accent-purple)]/10'
            )}>
              {planStatus === 'approved'
                ? <CheckCircle2 className="w-5 h-5 text-[var(--success)]" />
                : <Bot className="w-5 h-5 text-[var(--accent-purple)]" />}
            </div>
            <div>
              <p className="text-sm font-semibold text-[var(--text-primary)]">
                {planStatus === 'approved'
                  ? 'Migration plan approved — Bedrock Nova will execute autonomously'
                  : planStatus === 'changes'
                    ? 'Changes requested — Nova will revise the plan'
                    : 'Migration plan ready for review'}
              </p>
              <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
                {planStatus === 'approved'
                  ? 'Nova runs the full pipeline: Analyze → Decompose → Generate → Provision → Validate → Rollback.'
                  : 'Review the pipeline report and execution waves, then approve to start the autonomous migration.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {planStatus !== 'approved' && (
              <Button
                variant="outline"
                onClick={() => setPlanStatus('changes')}
                disabled={planStatus === 'changes'}
              >
                Request Changes
              </Button>
            )}
            <Button
              variant={planStatus === 'approved' ? 'outline' : 'primary'}
              className="gap-2"
              onClick={() => setPlanStatus(planStatus === 'approved' ? 'review' : 'approved')}
            >
              <ThumbsUp className="w-4 h-4" />
              {planStatus === 'approved' ? 'Revoke Approval' : 'Approve & Start Migration'}
            </Button>
          </div>
        </div>
      </motion.div>

      {/* Stats bar — AI execution metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { icon: Box, label: 'Services to Migrate', value: totalServices, color: 'bg-[var(--info-bg)] text-[var(--accent-blue)]' },
          { icon: Layers, label: 'Migration Waves', value: cost?.migration_impact?.total_waves ?? waves.length, color: 'bg-[var(--success-bg)] text-[var(--success)]' },
          { icon: Cloud, label: 'AWS Target Services', value: totalAwsServices, color: 'bg-[var(--warning-bg)] text-[var(--warning)]' },
          { icon: Sparkles, label: 'Pipeline Phases', value: PIPELINE.length, color: 'bg-[var(--accent-purple)]/10 text-[var(--accent-purple)]' },
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

      {/* Pipeline report */}
      <GlassCard glow="purple">
        <GlassCardHeader className="flex-row items-center justify-between">
          <div>
            <GlassCardTitle>How the Migration Runs</GlassCardTitle>
            <p className="text-sm text-[var(--text-secondary)] mt-0.5">
              Six-phase autonomous pipeline executed end-to-end by Amazon Bedrock Nova
            </p>
          </div>
          <Badge variant="premium" className="shrink-0">amazon.nova-pro</Badge>
        </GlassCardHeader>
        <GlassCardContent>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {PIPELINE.map((phase) => (
              <motion.div
                key={phase.step}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: phase.step * 0.06, duration: 0.3 }}
                className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-base)] p-4 flex flex-col"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${phase.color}14` }}>
                      <phase.icon className="w-4.5 h-4.5" style={{ color: phase.color }} />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-[var(--text-primary)] leading-none">
                        <span className="text-[var(--text-muted)] mr-1.5">{phase.step}.</span>{phase.name}
                      </p>
                      <p className="text-[10px] text-[var(--text-secondary)] mt-1">{phase.tagline}</p>
                    </div>
                  </div>
                  {phase.step < PIPELINE.length ? (
                    <span className="text-[10px] text-[var(--text-muted)]">→</span>
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-[var(--success)]" />
                  )}
                </div>

                <div className="space-y-1.5 mb-3">
                  {phase.whatNovaDoes.map((line) => (
                    <p key={line} className="text-[11px] text-[var(--text-secondary)] flex gap-1.5">
                      <span className="w-1 h-1 rounded-full mt-1 shrink-0" style={{ backgroundColor: phase.color }} />
                      {line}
                    </p>
                  ))}
                </div>

                <div className="mt-auto pt-3 border-t border-[var(--border-subtle)]">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)] mb-1.5">Outputs</p>
                  <div className="flex flex-wrap gap-1">
                    {phase.outputs.map((out) => (
                      <span key={out} className="px-1.5 py-0.5 rounded bg-[var(--border-subtle)]/60 text-[10px] text-[var(--text-secondary)]">{out}</span>
                    ))}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </GlassCardContent>
      </GlassCard>

      {/* Execution plan (waves) */}
      <GlassCard glow="blue">
        <GlassCardHeader>
          <GlassCardTitle>Execution Waves — Approved Sequence</GlassCardTitle>
          <p className="text-sm text-[var(--text-secondary)]">Nova migrates one wave at a time, validating and keeping each wave rollback-safe</p>
        </GlassCardHeader>
        <GlassCardContent>
          <div className="grid md:grid-cols-2 gap-3">
            {waves.map((wave: PlannerWave, i: number) => {
              const awsTargets = Object.values(wave.aws_services_map ?? {}).flat();
              return (
                <motion.div
                  key={wave.id || i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06, duration: 0.3 }}
                  onClick={() => setSelectedWave(wave)}
                  className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-base)] p-4 cursor-pointer hover:shadow-md hover:-translate-y-0.5 transition-all"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        'w-6 h-6 rounded flex items-center justify-center text-[11px] font-bold',
                        wave.risk_level === 'high' || wave.risk_level === 'critical' ? 'bg-[var(--danger-bg)] text-[var(--risk)]' :
                        wave.risk_level === 'medium' ? 'bg-[var(--warning-bg)] text-[var(--warning)]' : 'bg-[var(--success-bg)] text-[var(--success)]'
                      )}>W{wave.wave_number || i + 1}</span>
                      <span className="text-sm font-semibold text-[var(--text-primary)]">{wave.name}</span>
                    </div>
                    <RiskBadge risk={wave.risk_level} />
                  </div>

                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {(wave.services || []).map((svc: string, j: number) => (
                      <span key={j} className="px-2 py-0.5 rounded bg-[var(--border-subtle)] text-[11px] text-[var(--text-secondary)]">{svc}</span>
                    ))}
                  </div>

                  <div className="flex items-center gap-2 flex-wrap text-[10px] text-[var(--text-muted)]">
                    <span className="flex items-center gap-1"><Cloud className="w-3 h-3" /> {awsTargets.length} AWS targets</span>
                    {wave.dependencies?.length > 0 && (
                      <span className="flex items-center gap-1">
                        <span className="w-1 h-1 rounded-full bg-[var(--border-strong)]" />
                        After {wave.dependencies.join(', ')}
                      </span>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </GlassCardContent>
      </GlassCard>

      {/* AWS resource inventory */}
      {awsInventory.length > 0 && (
        <GlassCard glow="purple">
          <GlassCardHeader className="flex-row items-center justify-between">
            <div>
              <GlassCardTitle>AWS Resource Inventory</GlassCardTitle>
              <p className="text-sm text-[var(--text-secondary)] mt-0.5">
                {awsInventory.length} AWS services identified across the plan, grouped by category
              </p>
            </div>
            <Badge variant="premium" className="shrink-0">{totalAwsServices} targets</Badge>
          </GlassCardHeader>
          <GlassCardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {awsInventory.map((entry) => {
                const cat = CATS[entry.category];
                const Icon = cat.icon;
                return (
                  <motion.div
                    key={entry.service_name}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: entry.count * 0.02, duration: 0.3 }}
                    className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-base)] p-4"
                  >
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: `${cat.color}14` }}>
                          <Icon className="w-4 h-4" style={{ color: cat.color }} />
                        </div>
                        <span className="text-sm font-semibold text-[var(--text-primary)] truncate">{entry.service_name}</span>
                      </div>
                      <Badge variant="outline" size="sm">{entry.count}×</Badge>
                    </div>
                    <p className="text-[11px] text-[var(--accent-blue)] mb-2">{entry.use_case}</p>
                    <div className="flex flex-wrap gap-1 items-center">
                      {entry.waves.map((w) => (
                        <span key={w} className="px-1.5 py-0.5 rounded bg-[var(--border-subtle)] text-[10px] text-[var(--text-muted)]">W{w}</span>
                      ))}
                      <span className="text-[10px] text-[var(--text-muted)]">
                        {entry.microservices.join(', ')}
                      </span>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </GlassCardContent>
        </GlassCard>
      )}

      {/* Wave detail side panel */}
      {selectedWave && (
        <div className="fixed inset-0 z-50 bg-black/20 backdrop-blur-sm flex justify-end" onClick={() => setSelectedWave(null)}>
          <div className="w-96 bg-[var(--bg-elevated)] border-l border-[var(--border-subtle)] h-full overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-6">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className={cn(
                    'w-6 h-6 rounded flex items-center justify-center text-xs font-bold',
                    selectedWave.risk_level === 'high' || selectedWave.risk_level === 'critical' ? 'bg-[var(--danger-bg)] text-[var(--risk)]' :
                    selectedWave.risk_level === 'medium' ? 'bg-[var(--warning-bg)] text-[var(--warning)]' : 'bg-[var(--success-bg)] text-[var(--success)]'
                  )}>W{selectedWave.wave_number || 1}</span>
                  <h3 className="text-base font-semibold text-[var(--text-primary)]">{selectedWave.name}</h3>
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  <RiskBadge risk={selectedWave.risk_level} />
                  {selectedWave.migration_complexity && (
                    <Badge variant="secondary" size="sm">{selectedWave.migration_complexity} complexity</Badge>
                  )}
                </div>
              </div>
              <button onClick={() => setSelectedWave(null)} className="p-1 rounded hover:bg-[var(--border-subtle)] text-[var(--text-muted)]">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)] p-3 text-center">
                  <Box className="w-4 h-4 text-[var(--accent-blue)] mx-auto mb-1" />
                  <p className="text-lg font-bold text-[var(--text-primary)] tabular-nums">{selectedWave.services?.length ?? 0}</p>
                  <p className="text-[10px] text-[var(--text-muted)]">Services</p>
                </div>
                <div className="rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)] p-3 text-center">
                  <Cloud className="w-4 h-4 text-[var(--accent-blue)] mx-auto mb-1" />
                  <p className="text-lg font-bold text-[var(--text-primary)] tabular-nums">
                    {Object.values(selectedWave.aws_services_map ?? {}).flat().length || '-'}
                  </p>
                  <p className="text-[10px] text-[var(--text-muted)]">AWS Targets</p>
                </div>
              </div>

              {selectedWave.justification && selectedWave.justification.length > 0 && (
                <div className="rounded-lg bg-[var(--accent-purple)]/5 border border-[var(--accent-purple)]/20 p-3">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-[var(--accent-purple)]" />
                    <p className="text-xs font-semibold text-[var(--text-primary)]">Nova's Reasoning</p>
                  </div>
                  <ul className="space-y-1">
                    {selectedWave.justification.map((j: string, k: number) => (
                      <li key={k} className="text-[11px] text-[var(--text-secondary)]">• {j}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div>
                <p className="text-xs font-semibold text-[var(--text-primary)] mb-2">Services</p>
                <div className="flex flex-wrap gap-1.5">
                  {(selectedWave.services || []).map((svc: string, j: number) => (
                    <span key={j} className="px-2 py-0.5 rounded bg-[var(--border-subtle)] text-[11px] text-[var(--text-secondary)]">{svc}</span>
                  ))}
                </div>
              </div>

              {selectedWave.aws_services_map && Object.keys(selectedWave.aws_services_map).length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-[var(--text-primary)] mb-2">AWS Target Services</p>
                  <div className="space-y-2">
                    {(selectedWave.services || []).map((svc: string, j: number) => {
                      const targets = selectedWave.aws_services_map?.[svc];
                      if (!targets || targets.length === 0) return null;
                      return (
                        <div key={j}>
                          <p className="text-[11px] font-medium text-[var(--text-secondary)] mb-1">{svc}</p>
                          <div className="flex flex-wrap gap-1.5">
                            {targets.map((target: string, k: number) => (
                              <span key={k} className="px-2 py-0.5 rounded bg-[var(--border-subtle)] text-[11px] text-[var(--text-muted)]">{target}</span>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {selectedWave.dependencies?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-[var(--text-primary)] mb-2">Dependencies</p>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {selectedWave.dependencies.map((dep: string) => (
                      <span key={dep} className="px-1.5 py-0.5 rounded bg-[var(--border-subtle)] text-[11px] text-[var(--text-muted)]">{dep}</span>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2 pt-4 border-t border-[var(--border-subtle)]">
                <Badge variant={selectedWave.status === 'completed' ? 'success' : selectedWave.status === 'in_progress' ? 'info' : 'secondary'} size="sm">
                  {(selectedWave.status || 'planned').replace('_', ' ')}
                </Badge>
                {(selectedWave.progress ?? 0) > 0 && (
                  <span className="text-xs text-[var(--text-muted)]">{selectedWave.progress}% complete</span>
                )}
              </div>
            </div>

            {selectedJob && (
              <div className="mt-6">
                <Link to={`/jobs/${selectedJob.job_id}/results`}>
                  <Button variant="outline" className="gap-2 w-full">
                    View Full Results <Route className="w-4 h-4" />
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      )}

      {waves.length > 0 && selectedJob && (
        <div className="flex items-center justify-center">
          <Link to={`/jobs/${selectedJob.job_id}/results`}>
            <Button variant="outline" className="gap-2">
              View Detailed Results <Route className="w-4 h-4" />
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
}
