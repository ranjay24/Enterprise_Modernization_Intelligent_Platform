import { useState, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { GitBranch, ArrowRight, Box, Database, AlertTriangle, X, ExternalLink, Layers, Code2 } from 'lucide-react';
import { listJobs, getAnalysisResults } from '@/services/jobService';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ReadinessBadge, RiskBadge } from '@/components/cards';
import { EmptyState } from '@/components/common/EmptyState';
import { TableSkeleton } from '@/components/common/LoadingSkeleton';
import { cn } from '@/utils/cn';

const nodeTypeColors: Record<string, string> = {
  service: 'var(--architecture)',
  database: 'var(--analytics)',
  queue: 'var(--warning)',
  api: 'var(--accent-blue)',
};

function ServiceNode({ data }: NodeProps) {
  const svc = data.service;
  const color = nodeTypeColors[data.nodeType] || 'var(--architecture)';

  return (
    <div
      className="px-4 py-3 rounded-xl border-2 bg-[var(--bg-card)] shadow-md cursor-pointer hover:shadow-lg transition-shadow min-w-[180px]"
      style={{ borderColor: color }}
    >
      <Handle type="target" position={Position.Top} className="!bg-[var(--border-strong)]" />
      <div className="flex items-center gap-2 mb-1.5">
        <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
        <span className="text-xs font-semibold text-[var(--text-primary)] truncate">{svc.name}</span>
      </div>
      {svc.cohesion_score != null && (
        <div className="flex items-center gap-2 text-[10px] text-[var(--text-muted)]">
          <span>Cohesion: <span className="font-medium text-[var(--text-primary)]">{svc.cohesion_score}</span></span>
          <span>Coupling: <span className="font-medium text-[var(--text-primary)]">{svc.coupling_score}</span></span>
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-[var(--border-strong)]" />
    </div>
  );
}

const nodeTypes = { service: ServiceNode };

export default function ArchitecturePage() {
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

  const services = useMemo(() => (results?.service_boundaries || []) as any[], [results]);
  const metrics = useMemo(() => (results?.metrics || {}) as any, [results]);
  const circularDeps = useMemo(() => metrics.circular_dependencies || [], [metrics]);

  // React-Flow nodes and edges
  const initialNodes: Node[] = useMemo(() => services.map((svc: any, i: number) => ({
    id: svc.name || `svc-${i}`,
    type: 'service',
    position: {
      x: 200 + (i % 3) * 280,
      y: 80 + Math.floor(i / 3) * 160,
    },
    data: { service: svc, nodeType: 'service' },
  })), [services]);

  const initialEdges: Edge[] = useMemo(() => {
    const edges: Edge[] = [];
    services.forEach((svc: any, i: number) => {
      if (svc.dependencies) {
        svc.dependencies.forEach((dep: string) => {
          edges.push({
            id: `${svc.name}-${dep}`,
            source: svc.name,
            target: dep,
            animated: true,
            style: { stroke: 'var(--border-strong)', strokeWidth: 1.5 },
          });
        });
      }
    });
    return edges;
  }, [services]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedService, setSelectedService] = useState<any>(null);

  const onNodeClick = useCallback((_: any, node: Node) => {
    setSelectedService(node.data.service);
  }, []);

  if (isLoading) return <div className="p-6 lg:p-8 max-w-[1440px] mx-auto"><TableSkeleton rows={5} /></div>;

  if (!results) {
    return (
      <div className="p-6 lg:p-8 max-w-[1440px] mx-auto">
        <h1 className="text-[var(--font-size-3xl)] font-bold tracking-tight text-[var(--text-primary)] mb-1">Architecture</h1>
        <p className="text-sm text-[var(--text-secondary)] mb-8">Service boundary analysis and dependency mapping</p>
        <EmptyState
          icon={<GitBranch className="w-8 h-8" />}
          title="No architecture data"
          description="Run an analysis to view service boundaries and architecture insights."
          action={<Link to="/upload"><Button variant="primary">Analyze Codebase</Button></Link>}
        />
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-[1440px] mx-auto space-y-8">
      <div>
        <h1 className="text-[var(--font-size-3xl)] font-bold tracking-tight text-[var(--text-primary)] mb-1">Architecture</h1>
        <p className="text-sm text-[var(--text-secondary)]">Interactive service boundary graph with dependency mapping</p>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { icon: Box, label: 'Services Identified', value: services.length, color: 'bg-[var(--info-bg)] text-[var(--accent-blue)]' },
          { icon: Database, label: 'Total Classes', value: metrics.total_classes || 0, color: 'bg-[var(--success-bg)] text-[var(--success)]' },
          { icon: AlertTriangle, label: 'Circular Dependencies', value: circularDeps.length, color: circularDeps.length > 0 ? 'bg-[var(--danger-bg)] text-[var(--risk)]' : 'bg-[var(--border-subtle)] text-[var(--text-muted)]' },
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

      {/* Graph + side panel */}
      <div className="flex gap-4">
        <div className="flex-1 h-[500px] rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] overflow-hidden">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            onNodeClick={onNodeClick}
            fitView
            attributionPosition="bottom-left"
          >
            <Background color="var(--border-subtle)" gap={20} />
            <Controls className="!bg-[var(--bg-card)] !border-[var(--border-subtle)]" />
            <MiniMap
              className="!border-[var(--border-subtle)]"
              nodeColor={() => 'var(--architecture)'}
              maskColor="rgba(0,0,0,0.1)"
            />
          </ReactFlow>
        </div>

        {/* Side panel */}
        {selectedService && (
          <div className="w-80 shrink-0 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-5 h-fit">
            <div className="flex items-start justify-between mb-4">
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">{selectedService.name}</h3>
              <button
                onClick={() => setSelectedService(null)}
                className="p-1 rounded hover:bg-[var(--border-subtle)] text-[var(--text-muted)]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-[var(--text-secondary)] mb-4">{selectedService.description}</p>

            {selectedService.business_capability && (
              <Badge variant="info" size="sm" className="mb-3">{selectedService.business_capability}</Badge>
            )}

            <div className="grid grid-cols-2 gap-2 mb-4">
              {[
                { label: 'Cohesion', value: selectedService.cohesion_score || 0, color: (selectedService.cohesion_score || 0) >= 70 ? 'text-[var(--success)]' : 'text-[var(--warning)]' },
                { label: 'Coupling', value: selectedService.coupling_score || 0, color: (selectedService.coupling_score || 0) <= 30 ? 'text-[var(--success)]' : 'text-[var(--warning)]' },
                { label: 'Confidence', value: `${selectedService.confidence || 0}%`, color: (selectedService.confidence || 0) >= 80 ? 'text-[var(--success)]' : 'text-[var(--warning)]' },
                { label: 'Classes', value: (selectedService.classes || []).length, color: 'text-[var(--text-primary)]' },
              ].map((m) => (
                <div key={m.label} className="rounded-lg bg-[var(--border-subtle)]/50 p-2.5 text-center">
                  <div className={cn('text-base font-bold tabular-nums', m.color)}>{m.value}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">{m.label}</div>
                </div>
              ))}
            </div>

            <div className="space-y-1.5 text-[11px] text-[var(--text-muted)] mb-4">
              {selectedService.api_endpoints?.length > 0 && (
                <p><span className="font-medium text-[var(--text-primary)]">Endpoints:</span>{' '}
                  {selectedService.api_endpoints.map((ep: any) => `${ep.method || 'GET'} ${ep.path || ep.handler_class || ''}`).join(', ')}
                </p>
              )}
              <p><span className="font-medium text-[var(--text-primary)]">Packages:</span> {(selectedService.packages || []).join(', ') || 'N/A'}</p>
              {selectedService.database_tables?.length > 0 && (
                <p><span className="font-medium text-[var(--text-primary)]">Tables:</span> {selectedService.database_tables.join(', ')}</p>
              )}
            </div>

            <div className="flex items-center gap-2">
              <ReadinessBadge readiness={selectedService.readiness} />
              <RiskBadge risk={selectedService.risk_level} />
            </div>

            {latestJob && (
              <div className="mt-4 pt-3 border-t border-[var(--border-subtle)]">
                <Link to={`/jobs/${latestJob.job_id}/results`}>
                  <Button variant="ghost" size="sm" className="gap-1.5 text-xs">
                    View Full Results <ExternalLink className="w-3.5 h-3.5" />
                  </Button>
                </Link>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
