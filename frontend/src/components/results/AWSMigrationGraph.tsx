import { useEffect, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useNodesState, useEdgesState } from 'reactflow';
import {
  Activity,
  Cloud,
  Database,
  Layers,
  Radio,
  Route,
  Server,
  X,
} from 'lucide-react';
import type { MigrationWave, AWSServiceRecommendation, ServiceBoundary } from '@/types/api';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/utils/cn';

type AwsCategory = 'gateway' | 'compute' | 'database' | 'messaging' | 'observability' | 'other';

const categoryStyles: Record<AwsCategory, { color: string; border: string; icon: JSX.Element }> = {
  gateway: { color: 'var(--accent-purple)', border: 'var(--accent-purple)', icon: <Route className="w-3.5 h-3.5" /> },
  compute: { color: 'var(--accent-blue)', border: 'var(--accent-blue)', icon: <Server className="w-3.5 h-3.5" /> },
  database: { color: 'var(--analytics)', border: 'var(--analytics)', icon: <Database className="w-3.5 h-3.5" /> },
  messaging: { color: 'var(--warning)', border: 'var(--warning)', icon: <Radio className="w-3.5 h-3.5" /> },
  observability: { color: 'var(--success)', border: 'var(--success)', icon: <Activity className="w-3.5 h-3.5" /> },
  other: { color: 'var(--text-secondary)', border: 'var(--border-strong)', icon: <Cloud className="w-3.5 h-3.5" /> },
};

function awsCategory(serviceName: string): AwsCategory {
  const n = serviceName.toLowerCase();
  if (n.includes('api gateway')) return 'gateway';
  if (n.includes('lambda') || n.includes('ecs') || n.includes('fargate') || n.includes('ec2') || n.includes('eks')) return 'compute';
  if (n.includes('rds') || n.includes('dynamo') || n.includes('aurora') || n.includes('documentdb') || n.includes('neptune') || n.includes('elasticache') || n.includes('redis')) return 'database';
  if (n.includes('sns') || n.includes('sqs') || n.includes('msk') || n.includes('kafka') || n.includes('eventbridge') || n.includes('mq')) return 'messaging';
  if (n.includes('cloudwatch') || n.includes('x-ray')) return 'observability';
  return 'other';
}

const ROW_H = 110;

interface BuiltGraph {
  nodes: Node[];
  edges: Edge[];
}

function buildGraph(waves: MigrationWave[]): BuiltGraph {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  let waveBaseY = 50;

  waves.forEach((wave) => {
    const services = wave.services || [];
    const recsByService = wave.aws_recommendations || {};
    const waveId = `wave-${wave.wave_number}`;

    const serviceLayouts = services.map((svc) => {
      const recs = recsByService[svc] || [];
      const rows = Math.max(1, Math.ceil(recs.length / 2));
      return { svc, recs, rows, height: rows * ROW_H + 70 };
    });
    const waveBlockH = serviceLayouts.reduce((acc, s) => acc + s.height, 0);

    nodes.push({
      id: waveId,
      type: 'wave',
      position: { x: 40, y: waveBaseY + waveBlockH / 2 - 45 },
      data: { wave },
    });

    let svcY = waveBaseY;
    serviceLayouts.forEach(({ svc, recs, rows }) => {
      const svcId = `svc-${wave.wave_number}-${svc}`;
      nodes.push({
        id: svcId,
        type: 'service',
        position: { x: 330, y: svcY + 20 },
        data: { service: svc, wave },
      });
      edges.push({
        id: `e-${waveId}-${svcId}`,
        source: waveId,
        target: svcId,
        animated: false,
        style: { stroke: 'var(--border-strong)', strokeWidth: 1.2, strokeDasharray: '4 4' },
      });

      recs.forEach((rec, i) => {
        const awsId = `aws-${wave.wave_number}-${svc}-${i}`;
        const col = i % 2;
        const row = Math.floor(i / 2);
        const cat = awsCategory(rec.service_name);
        nodes.push({
          id: awsId,
          type: 'aws',
          position: { x: 640 + col * 250, y: svcY + 10 + row * ROW_H },
          data: { rec, service: svc, wave },
        });
        edges.push({
          id: `e-${svcId}-${awsId}`,
          source: svcId,
          target: awsId,
          animated: true,
          style: { stroke: categoryStyles[cat].border, strokeWidth: 1.5 },
        });
      });

      svcY += rows * ROW_H + 70;
    });

    waveBaseY = svcY + 80;
  });

  return { nodes, edges };
}

function WaveNode({ data }: NodeProps) {
  const wave = data.wave as MigrationWave;
  return (
    <div className="px-3 py-2.5 rounded-xl border-2 border-[var(--accent-purple)] bg-[var(--bg-card)] shadow-md min-w-[150px]">
      <Handle type="source" position={Position.Right} className="!bg-[var(--accent-purple)]" />
      <div className="flex items-center gap-2 mb-1">
        <Layers className="w-4 h-4 text-[var(--accent-purple)]" />
        <span className="text-xs font-bold text-[var(--accent-purple)]">W{wave.wave_number}</span>
      </div>
      <p className="text-[10px] font-medium text-[var(--text-primary)] truncate max-w-[130px]">{wave.name}</p>
      <div className="flex items-center gap-1.5 mt-1">
        <Badge variant="outline" size="sm">{wave.services?.length || 0} svc</Badge>
        <span className="text-[9px] text-[var(--text-muted)]">{wave.timeline_weeks} wks</span>
      </div>
    </div>
  );
}

function ServiceNode({ data }: NodeProps) {
  const service = data.service as string;
  const wave = data.wave as MigrationWave;
  return (
    <div className="px-3 py-2 rounded-xl border-2 border-[var(--architecture)] bg-[var(--bg-card)] shadow-md min-w-[180px]">
      <Handle type="target" position={Position.Left} className="!bg-[var(--border-strong)]" />
      <Handle type="source" position={Position.Right} className="!bg-[var(--border-strong)]" />
      <div className="flex items-center gap-2">
        <Server className="w-4 h-4 text-[var(--architecture)] shrink-0" />
        <span className="text-xs font-semibold text-[var(--text-primary)] truncate">{service}</span>
      </div>
      <span className="text-[9px] text-[var(--text-muted)]">W{wave.wave_number}</span>
    </div>
  );
}

function AWSNode({ data }: NodeProps) {
  const rec = data.rec as AWSServiceRecommendation;
  const style = categoryStyles[awsCategory(rec.service_name)];
  return (
    <div
      className="px-3 py-2 rounded-xl border-2 bg-[var(--bg-card)] shadow-md min-w-[180px] cursor-pointer hover:shadow-lg transition-shadow"
      style={{ borderColor: style.border }}
    >
      <Handle type="target" position={Position.Left} className="!bg-[var(--border-strong)]" />
      <div className="flex items-center gap-2 mb-0.5">
        <span className="shrink-0" style={{ color: style.color }}>{style.icon}</span>
        <span className="text-[11px] font-semibold text-[var(--text-primary)] truncate">{rec.service_name}</span>
      </div>
      <span className="text-[9px] block truncate" style={{ color: style.color }}>{rec.use_case}</span>
    </div>
  );
}

const nodeTypes = { wave: WaveNode, service: ServiceNode, aws: AWSNode };

type Selection =
  | { kind: 'wave'; wave: MigrationWave }
  | { kind: 'service'; service: string; wave: MigrationWave }
  | { kind: 'aws'; rec: AWSServiceRecommendation; service: string; wave: MigrationWave };

interface AWSMigrationGraphProps {
  waves: MigrationWave[];
  services?: ServiceBoundary[];
  height?: string;
}

export function AWSMigrationGraph({ waves, services, height = 'h-[560px]' }: AWSMigrationGraphProps) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => buildGraph(waves), [waves]);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selected, setSelected] = useState<Selection | null>(null);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
    setSelected(null);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const descriptionByService = useMemo(
    () => new Map((services || []).map((svc) => [svc.name, svc.description])),
    [services]
  );

  const onNodeClick = (_: unknown, node: Node) => {
    const d = node.data as { rec?: AWSServiceRecommendation; service?: string; wave?: MigrationWave };
    if (node.type === 'aws' && d.rec && d.service && d.wave) {
      setSelected({ kind: 'aws', rec: d.rec, service: d.service, wave: d.wave });
    } else if (node.type === 'service' && d.service && d.wave) {
      setSelected({ kind: 'service', service: d.service, wave: d.wave });
    } else if (node.type === 'wave' && d.wave) {
      setSelected({ kind: 'wave', wave: d.wave });
    }
  };

  return (
    <div className={cn('rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] overflow-hidden relative', height)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.2}
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="var(--border-subtle)" gap={20} />
        <Controls className="!bg-[var(--bg-card)] !border-[var(--border-subtle)]" />
        <MiniMap
          className="!border-[var(--border-subtle)]"
          nodeColor={(n) => {
            const d = n.data as { rec?: unknown; service?: unknown };
            if (d.rec) return 'var(--accent-blue)';
            if (d.service) return 'var(--architecture)';
            return 'var(--accent-purple)';
          }}
          maskColor="rgba(0,0,0,0.1)"
        />
      </ReactFlow>

      {selected && (
        <SelectionPanel
          selection={selected}
          onClose={() => setSelected(null)}
          description={selected.kind === 'service' ? descriptionByService.get(selected.service) : undefined}
        />
      )}
    </div>
  );
}

function SelectionPanel({
  selection,
  onClose,
  description,
}: {
  selection: Selection;
  onClose: () => void;
  description?: string;
}) {
  return (
    <div className="absolute top-3 right-3 w-[300px] max-h-[calc(100%-24px)] overflow-y-auto rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4 shadow-xl z-10">
      <div className="flex items-start justify-between mb-3">
        <h4 className="text-sm font-semibold text-[var(--text-primary)]">
          {selection.kind === 'wave' && `Wave ${selection.wave.wave_number} · ${selection.wave.name}`}
          {selection.kind === 'service' && selection.service}
          {selection.kind === 'aws' && selection.rec.service_name}
        </h4>
        <button onClick={onClose} className="p-1 rounded hover:bg-[var(--border-subtle)] text-[var(--text-muted)]">
          <X className="w-4 h-4" />
        </button>
      </div>

      {selection.kind === 'wave' && (
        <div className="space-y-2 text-xs text-[var(--text-secondary)]">
          <div className="flex flex-wrap gap-1.5">
            <Badge variant="outline" size="sm">{selection.wave.risk_level} risk</Badge>
            <Badge variant="outline" size="sm">{selection.wave.timeline_weeks} weeks</Badge>
            <Badge variant="outline" size="sm">{selection.wave.estimated_engineers} engineers</Badge>
          </div>
          {selection.wave.dependencies?.length > 0 && (
            <p><span className="font-medium text-[var(--text-primary)]">Depends on:</span> {selection.wave.dependencies.join(', ')}</p>
          )}
          {selection.wave.services?.length > 0 && (
            <div>
              <p className="font-medium text-[var(--text-primary)] mb-1">Services:</p>
              <div className="flex flex-wrap gap-1">
                {selection.wave.services.map((s) => (
                  <span key={s} className="px-1.5 py-0.5 rounded bg-[var(--border-subtle)] text-[10px] text-[var(--text-secondary)]">{s}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {selection.kind === 'service' && (
        <div className="space-y-2 text-xs text-[var(--text-secondary)]">
          {description && <p>{description}</p>}
          <p><span className="font-medium text-[var(--text-primary)]">Wave:</span> W{selection.wave.wave_number}</p>
          {(selection.wave.aws_recommendations?.[selection.service] || []).length > 0 && (
            <div>
              <p className="font-medium text-[var(--text-primary)] mb-1">AWS services:</p>
              <div className="space-y-1">
                {(selection.wave.aws_recommendations![selection.service] || []).map((rec, i) => (
                  <div key={i} className="flex items-center justify-between gap-2">
                    <span className="truncate">{rec.service_name}</span>
                    <span className="text-[10px] text-[var(--text-muted)] shrink-0">{rec.use_case}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {selection.kind === 'aws' && (
        <div className="space-y-2 text-xs text-[var(--text-secondary)]">
          <p><span className="font-medium text-[var(--text-primary)]">Use case:</span> {selection.rec.use_case}</p>
          <p><span className="font-medium text-[var(--text-primary)]">Justification:</span> {selection.rec.justification}</p>
          <div className="flex flex-wrap gap-1.5">
            {selection.rec.pricing_model && <Badge variant="info" size="sm">{selection.rec.pricing_model}</Badge>}
            <Badge variant="outline" size="sm">W{selection.wave.wave_number}</Badge>
          </div>
          {selection.rec.alternatives && selection.rec.alternatives.length > 0 && (
            <div>
              <p className="font-medium text-[var(--text-primary)] mb-1">Alternatives:</p>
              <div className="flex flex-wrap gap-1">
                {selection.rec.alternatives.map((alt, i) => (
                  <span key={i} className="px-1.5 py-0.5 rounded bg-[var(--border-subtle)] text-[10px] text-[var(--text-secondary)]">{alt}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function AWSMigrationLegend() {
  const items = [
    { label: 'Migration Wave', color: 'var(--accent-purple)', icon: <Layers className="w-3.5 h-3.5" /> },
    { label: 'Service', color: 'var(--architecture)', icon: <Server className="w-3.5 h-3.5" /> },
    { label: 'API Gateway', color: 'var(--accent-purple)', icon: <Route className="w-3.5 h-3.5" /> },
    { label: 'Compute', color: 'var(--accent-blue)', icon: <Server className="w-3.5 h-3.5" /> },
    { label: 'Database', color: 'var(--analytics)', icon: <Database className="w-3.5 h-3.5" /> },
    { label: 'Messaging', color: 'var(--warning)', icon: <Radio className="w-3.5 h-3.5" /> },
    { label: 'Observability', color: 'var(--success)', icon: <Activity className="w-3.5 h-3.5" /> },
  ];
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5">
      {items.map((it) => (
        <span key={it.label} className="inline-flex items-center gap-1.5 text-[10px] text-[var(--text-muted)]">
          <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: it.color }} />
          {it.label}
        </span>
      ))}
    </div>
  );
}
