import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Layers, ArrowRight, Clock, Users, AlertTriangle, X, ExternalLink, DollarSign, CheckCircle2 } from 'lucide-react';
import { listJobs, getAnalysisResults } from '@/services/jobService';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { RiskBadge } from '@/components/cards';
import { EmptyState } from '@/components/common/EmptyState';
import { TableSkeleton } from '@/components/common/LoadingSkeleton';
import { GlassCard, GlassCardContent, GlassCardHeader, GlassCardTitle } from '@/components/ui/GlassCard';
import { cn } from '@/utils/cn';

const riskColors: Record<string, string> = {
  low: 'bg-[var(--success)]',
  medium: 'bg-[var(--warning)]',
  high: 'bg-[var(--risk)]',
  critical: 'bg-[var(--risk)]',
};

const statusIcons: Record<string, React.ElementType> = {
  completed: CheckCircle2,
  in_progress: Clock,
  planned: Clock,
  blocked: AlertTriangle,
};

const statusColors: Record<string, string> = {
  completed: 'text-[var(--success)]',
  in_progress: 'text-[var(--accent-blue)]',
  planned: 'text-[var(--text-muted)]',
  blocked: 'text-[var(--risk)]',
};

export default function MigrationPlannerPage() {
  const { data: jobsData, isLoading: jobsLoading } = useQuery({
    queryKey: ['jobs'], queryFn: listJobs, staleTime: 30000,
  });

  const completedJobs = (jobsData?.jobs || []).filter((j: any) => j.status === 'analysis_complete');
  const latestJob = completedJobs[0];

  const { data: results, isLoading: resultsLoading } = useQuery({
    queryKey: ['analysis', latestJob?.job_id],
    queryFn: () => getAnalysisResults(latestJob!.job_id),
    enabled: !!latestJob, staleTime: 60000,
  });

  const isLoading = jobsLoading || resultsLoading;

  const [selectedWave, setSelectedWave] = useState<any>(null);

  if (isLoading) return <div className="p-6 lg:p-8 max-w-[1440px] mx-auto"><TableSkeleton rows={5} /></div>;

  if (!results) {
    return (
      <div className="p-6 lg:p-8 max-w-[1440px] mx-auto">
        <h1 className="text-[var(--font-size-3xl)] font-bold tracking-tight text-[var(--text-primary)] mb-1">Migration Planner</h1>
        <p className="text-sm text-[var(--text-secondary)] mb-8">Phased migration plan with waves, timelines, and risk assessment</p>
        <EmptyState
          icon={<Layers className="w-8 h-8" />}
          title="No migration plan"
          description="Run an analysis to generate a phased migration plan."
          action={<Link to="/upload"><Button variant="primary">Analyze Codebase</Button></Link>}
        />
      </div>
    );
  }

  const waves = (results.migration_waves || []) as any[];
  const cost = results.cost_comparison;
  const maxWeek = Math.max(...waves.map((w: any) => w.durationWeeks?.end || w.timeline_weeks || 12), 12);

  return (
    <div className="p-6 lg:p-8 max-w-[1440px] mx-auto space-y-8">
      <div>
        <h1 className="text-[var(--font-size-3xl)] font-bold tracking-tight text-[var(--text-primary)] mb-1">Migration Planner</h1>
        <p className="text-sm text-[var(--text-secondary)]">Phased migration plan with waves, timelines, and risk assessment</p>
      </div>

      {/* Stats bar */}
      {cost?.migration_impact && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { icon: Layers, label: 'Services', value: cost.migration_impact.total_services, color: 'bg-[var(--info-bg)] text-[var(--accent-blue)]' },
            { icon: Layers, label: 'Waves', value: cost.migration_impact.total_waves, color: 'bg-[var(--success-bg)] text-[var(--success)]' },
            { icon: Clock, label: 'Timeline', value: `${cost.migration_impact.estimated_timeline_weeks}w`, color: 'bg-[var(--warning-bg)] text-[var(--warning)]' },
            { icon: Users, label: 'Engineers Needed', value: cost.migration_impact.total_engineers_needed, color: 'bg-[var(--accent-purple)]/10 text-[var(--accent-purple)]' },
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
      )}

      {/* Gantt-style timeline */}
      <GlassCard glow="blue">
        <GlassCardHeader>
          <GlassCardTitle>Migration Waves — {maxWeek} Week Timeline</GlassCardTitle>
        </GlassCardHeader>
        <GlassCardContent>
          <div className="space-y-4">
            {/* Timeline header */}
            <div className="flex items-center gap-3 pl-24">
              {Array.from({ length: Math.min(maxWeek, 14) }, (_, i) => (
                <div key={i} className="flex-1 text-[9px] text-[var(--text-muted)] text-center font-mono">
                  W{i + 1}
                </div>
              ))}
              {maxWeek > 14 && (
                <div className="text-[9px] text-[var(--text-muted)]">...</div>
              )}
            </div>

            {/* Wave bars */}
            {waves.map((wave: any, i: number) => {
              const startWeek = wave.durationWeeks?.start || 1;
              const endWeek = wave.durationWeeks?.end || (wave.timeline_weeks || 4) + (i * 2);
              const waveWidth = ((endWeek - startWeek + 1) / Math.min(maxWeek, 14)) * 100;
              const leftOffset = ((startWeek - 1) / Math.min(maxWeek, 14)) * 100;
              const Icon = statusIcons[wave.status] || Clock;

              return (
                <motion.div
                  key={wave.id || i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.08, duration: 0.3 }}
                >
                  <div className="flex items-center gap-3 group cursor-pointer" onClick={() => setSelectedWave(wave)}>
                    <div className="w-24 shrink-0 flex items-center gap-2">
                      <span className={cn(
                        'w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold',
                        wave.risk_level === 'high' || wave.risk_level === 'critical' ? 'bg-[var(--danger-bg)] text-[var(--risk)]' :
                        wave.risk_level === 'medium' ? 'bg-[var(--warning-bg)] text-[var(--warning)]' : 'bg-[var(--success-bg)] text-[var(--success)]'
                      )}>W{wave.wave_number || i + 1}</span>
                      <span className="text-xs font-medium text-[var(--text-primary)] truncate">{wave.name}</span>
                    </div>
                    <div className="flex-1 h-7 relative bg-[var(--border-subtle)] rounded-md overflow-hidden">
                      <div
                        className={cn('absolute top-0 h-full rounded-md transition-all duration-500', riskColors[wave.risk_level] || 'bg-[var(--border-strong)]')}
                        style={{ left: `${leftOffset}%`, width: `${waveWidth}%`, opacity: wave.status === 'planned' ? 0.5 : 0.85 }}
                      />
                      {wave.progress > 0 && (
                        <div
                          className={cn('absolute top-0 h-full rounded-md transition-all duration-700 ease-[var(--ease-out)]', riskColors[wave.risk_level] || 'bg-[var(--border-strong)]')}
                          style={{ left: `${leftOffset}%`, width: `${(wave.progress / 100) * waveWidth}%`, opacity: 1 }}
                        />
                      )}
                    </div>
                    <div className="flex items-center gap-2 w-28 shrink-0 justify-end">
                      <Icon className={cn('w-3.5 h-3.5', statusColors[wave.status] || 'text-[var(--text-muted)]')} />
                      <span className="text-[10px] text-[var(--text-muted)]">{endWeek - startWeek + 1}w</span>
                      <span className="text-[10px] text-[var(--text-muted)]">~{wave.estimated_engineers || wave.estimatedEngineers || '-'} eng</span>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 mt-5 text-[10px] text-[var(--text-muted)]">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-[var(--success)]" /> Low Risk</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-[var(--warning)]" /> Medium Risk</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-[var(--risk)]" /> High Risk</span>
          </div>
        </GlassCardContent>
      </GlassCard>

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
                <RiskBadge risk={selectedWave.risk_level} />
              </div>
              <button onClick={() => setSelectedWave(null)} className="p-1 rounded hover:bg-[var(--border-subtle)] text-[var(--text-muted)]">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)] p-3 text-center">
                  <Clock className="w-4 h-4 text-[var(--accent-blue)] mx-auto mb-1" />
                  <p className="text-lg font-bold text-[var(--text-primary)] tabular-nums">{selectedWave.timeline_weeks || (selectedWave.durationWeeks?.end - selectedWave.durationWeeks?.start + 1) || '-'}w</p>
                  <p className="text-[10px] text-[var(--text-muted)]">Duration</p>
                </div>
                <div className="rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)] p-3 text-center">
                  <Users className="w-4 h-4 text-[var(--accent-blue)] mx-auto mb-1" />
                  <p className="text-lg font-bold text-[var(--text-primary)] tabular-nums">~{selectedWave.estimated_engineers || selectedWave.estimatedEngineers || '-'}</p>
                  <p className="text-[10px] text-[var(--text-muted)]">Engineers</p>
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold text-[var(--text-primary)] mb-2">Services</p>
                <div className="flex flex-wrap gap-1.5">
                  {(selectedWave.services || []).map((svc: string, j: number) => (
                    <span key={j} className="px-2 py-0.5 rounded bg-[var(--border-subtle)] text-[11px] text-[var(--text-secondary)]">{svc}</span>
                  ))}
                </div>
              </div>

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

              {selectedWave.estimatedCost && (
                <div className="rounded-lg bg-[var(--success-bg)]/50 border border-[var(--success)]/20 p-3">
                  <DollarSign className="w-4 h-4 text-[var(--success)] mb-1" />
                  <p className="text-lg font-bold text-[var(--success)] tabular-nums">${(selectedWave.estimatedCost / 1000).toFixed(0)}k</p>
                  <p className="text-[10px] text-[var(--text-muted)]">Estimated Cost</p>
                </div>
              )}

              <div className="flex items-center gap-2 pt-4 border-t border-[var(--border-subtle)]">
                <Badge variant={selectedWave.status === 'completed' ? 'success' : selectedWave.status === 'in_progress' ? 'info' : 'secondary'} size="sm">
                  {(selectedWave.status || 'planned').replace('_', ' ')}
                </Badge>
                {selectedWave.progress > 0 && (
                  <span className="text-xs text-[var(--text-muted)]">{selectedWave.progress}% complete</span>
                )}
              </div>
            </div>

            {latestJob && (
              <div className="mt-6">
                <Link to={`/jobs/${latestJob.job_id}/results`}>
                  <Button variant="outline" className="gap-2 w-full">
                    View Full Results <ArrowRight className="w-4 h-4" />
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      )}

      {waves.length > 0 && latestJob && (
        <Link to={`/jobs/${latestJob.job_id}/results`} className="inline-block">
          <Button variant="outline" className="gap-2">
            View Detailed Results <ArrowRight className="w-4 h-4" />
          </Button>
        </Link>
      )}
    </div>
  );
}
