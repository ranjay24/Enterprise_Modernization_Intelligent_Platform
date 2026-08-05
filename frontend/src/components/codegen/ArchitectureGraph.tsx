import { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Database, Radio, Server, GitMerge, Route, Zap } from 'lucide-react';
import type { ArchitectureDesign } from '@/types';
import { cn } from '@/utils/cn';

const nodeTypeStyles: Record<string, string> = {
  gateway: 'border-[var(--accent-purple)] text-[var(--accent-purple)]',
  service: 'border-[var(--architecture)] text-[var(--architecture)]',
  database: 'border-[var(--analytics)] text-[var(--analytics)]',
  broker: 'border-[var(--warning)] text-[var(--warning)]',
};

const edgeTypeStyles: Record<string, { stroke: string; animated: boolean; dash: string }> = {
  rest: { stroke: 'var(--accent-blue)', animated: false, dash: '' },
  feign: { stroke: '#f97316', animated: false, dash: '8 4' },
  database: { stroke: 'var(--border-strong)', animated: false, dash: '' },
  publish: { stroke: '#ef4444', animated: true, dash: '6 4' },
  subscribe: { stroke: '#ec4899', animated: true, dash: '2 4' },
  queue: { stroke: '#a855f7', animated: true, dash: '4 4' },
};

function nodeIcon(type: string) {
  switch (type) {
    case 'gateway': return <Route className="w-4 h-4" />;
    case 'database': return <Database className="w-4 h-4" />;
    case 'broker': return <Radio className="w-4 h-4" />;
    default: return <Server className="w-4 h-4" />;
  }
}

function ArchitectureNode({ data }: NodeProps) {
  const node = data.design;
  const isService = node.type === 'service';
  const isBroker = node.type === 'broker';
  const isGateway = node.type === 'gateway';
  const colorClass = nodeTypeStyles[node.type] || nodeTypeStyles.service;

  return (
    <div
      className={cn(
        'px-3 py-2.5 rounded-xl border-2 bg-[var(--bg-card)] shadow-md min-w-[170px] transition-shadow hover:shadow-lg',
        colorClass
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-[var(--border-strong)]" />
      <div className="flex items-center gap-2 mb-1">
        {nodeIcon(node.type)}
        <span className="text-xs font-semibold text-[var(--text-primary)] truncate">{node.label || node.id}</span>
      </div>

      {isGateway && (
        <p className="text-[10px] text-[var(--text-muted)]">Single ingress / routing</p>
      )}

      {isBroker && (
        <div className="flex items-center gap-1.5 mt-0.5">
          <Zap className="w-3 h-3 text-[var(--warning)]" />
          <span className="text-[10px] font-medium uppercase tracking-wide text-[var(--warning)]">
            {node.subtype || node.label}
          </span>
        </div>
      )}

      {isService && (
        <div className="mt-1.5 space-y-1">
          {node.broker_role && node.broker_role !== 'none' && (
            <span
              className={cn(
                'inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase',
                node.broker_role === 'kafka' && 'bg-[var(--danger-bg)] text-[var(--risk)]',
                node.broker_role === 'rabbitmq' && 'bg-[var(--warning-bg)] text-[var(--warning)]',
                node.broker_role === 'both' && 'bg-[var(--info-bg)] text-[var(--accent-blue)]',
              )}
            >
              {node.broker_role}
            </span>
          )}
          {node.resilience && node.resilience.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {node.resilience.slice(0, 4).map((r: string) => (
                <span key={r} className="px-1 py-0 rounded bg-[var(--border-subtle)]/60 text-[9px] text-[var(--text-muted)]">
                  {r}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-[var(--border-strong)]" />
    </div>
  );
}

const nodeTypes = { architecture: ArchitectureNode };

interface ArchitectureGraphProps {
  design: ArchitectureDesign;
  onSelectNode?: (node: any) => void;
  height?: string;
}

export function ArchitectureGraph({ design, onSelectNode, height = 'h-[520px]' }: ArchitectureGraphProps) {
  const nodes: Node[] = useMemo(
    () =>
      (design.nodes || []).map((n, i) => ({
        id: n.id,
        type: 'architecture',
        position: { x: 200 + (i % 3) * 320, y: 80 + Math.floor(i / 3) * 190 },
        data: { design: n },
      })),
    [design]
  );

  const edges: Edge[] = useMemo(
    () =>
      (design.edges || []).map((e) => {
        const style = edgeTypeStyles[e.type] || edgeTypeStyles.rest;
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          animated: style.animated,
          label: e.label,
          labelStyle: { fill: 'var(--text-muted)', fontSize: 10 },
          labelBgStyle: { fill: 'var(--bg-card)', fillOpacity: 0.9 },
          style: {
            stroke: style.stroke,
            strokeWidth: 1.5,
            strokeDasharray: style.dash || undefined,
          },
        };
      }),
    [design]
  );

  const onNodeClick = (_: any, node: Node) => {
    if (onSelectNode) onSelectNode(node.data.design);
  };

  return (
    <div className={cn('rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] overflow-hidden', height)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        attributionPosition="bottom-left"
        minZoom={0.2}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="var(--border-subtle)" gap={20} />
        <Controls className="!bg-[var(--bg-card)] !border-[var(--border-subtle)]" />
        <MiniMap
          className="!border-[var(--border-subtle)]"
          nodeColor={(n) => {
            const t = (n as any).data?.design?.type;
            if (t === 'gateway') return 'var(--accent-purple)';
            if (t === 'database') return 'var(--analytics)';
            if (t === 'broker') return 'var(--warning)';
            return 'var(--architecture)';
          }}
          maskColor="rgba(0,0,0,0.1)"
        />
      </ReactFlow>
    </div>
  );
}

export function ArchitectureLegend() {
  const items = [
    { label: 'API Gateway', color: 'var(--accent-purple)', icon: <Route className="w-3.5 h-3.5" /> },
    { label: 'Service', color: 'var(--architecture)', icon: <Server className="w-3.5 h-3.5" /> },
    { label: 'Database', color: 'var(--analytics)', icon: <Database className="w-3.5 h-3.5" /> },
    { label: 'Broker (Kafka/Rabbit)', color: 'var(--warning)', icon: <Radio className="w-3.5 h-3.5" /> },
    { label: 'REST / Gateway', color: 'var(--accent-blue)', icon: <GitMerge className="w-3.5 h-3.5" /> },
    { label: 'Feign (sync)', color: '#f97316', icon: <GitMerge className="w-3.5 h-3.5" /> },
    { label: 'Publish / Subscribe', color: '#ef4444', icon: <GitMerge className="w-3.5 h-3.5" /> },
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
