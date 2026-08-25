import { useEffect, useMemo, useState } from 'react';
import {
  Sparkles,
  FileArchive,
  ScanLine,
  PartyPopper,
  Cloud,
  Boxes,
  Network,
  Waypoints,
  HardDrive,
  Database,
  MessageSquare,
  Zap,
  Upload,
  UploadCloud,
  Cpu,
  Activity,
} from 'lucide-react';
import { cn } from '@/utils/cn';

type SceneId = 'drop' | 'scan' | 'generated' | 'aws' | 'web';

interface Scene {
  id: SceneId;
  icon: React.ElementType;
  title: string;
  quote: string;
  duration: number;
}

const SCENES: Scene[] = [
  {
    id: 'drop',
    icon: FileArchive,
    title: 'Drop in your legacy monolith',
    quote: 'A single ZIP. Every class, method, and dependency lands in seconds.',
    duration: 2400,
  },
  {
    id: 'scan',
    icon: ScanLine,
    title: 'AI digs through everything',
    quote: 'Static analysis + domain mapping extract the real architecture.',
    duration: 2800,
  },
  {
    id: 'generated',
    icon: PartyPopper,
    title: 'Yay! Microservices generated',
    quote: 'Spring Boot services with clean boundaries, built from real code.',
    duration: 2500,
  },
  {
    id: 'aws',
    icon: Cloud,
    title: 'AWS services provisioned',
    quote: 'Lambda, API Gateway, S3, DynamoDB and more — ready to deploy.',
    duration: 2700,
  },
  {
    id: 'web',
    icon: Network,
    title: 'Your architecture, mapped',
    quote: 'Every service connected — a living web you can explore.',
    duration: 3600,
  },
];

const STEPS: { id: SceneId; label: string; icon: React.ElementType }[] = [
  { id: 'drop', label: 'Upload', icon: Upload },
  { id: 'scan', label: 'Analyze', icon: ScanLine },
  { id: 'generated', label: 'Generate', icon: Boxes },
  { id: 'aws', label: 'Migrate', icon: UploadCloud },
];

const STEP_INDEX: Record<SceneId, number> = {
  drop: 0,
  scan: 1,
  generated: 2,
  aws: 3,
  web: 3,
};

const CONFETTI_COLORS = ['#818CF8', '#A78BFA', '#60A5FA', '#F472B6', '#34D399', '#FBBF24'];

function useCountUp(target: number, active: boolean, duration = 1800): number {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!active) return;
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      setValue(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, active, duration]);
  return value;
}

function DropStage() {
  const [landed, setLanded] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setLanded(true), 1100);
    return () => clearTimeout(t);
  }, []);
  return (
    <div className="flex flex-col items-center pt-10">
      <div className={cn('relative', landed && 'animate-thud')}>
        <div className="animate-drop w-28 h-28 rounded-2xl bg-white/10 backdrop-blur border border-white/20 flex items-center justify-center shadow-2xl">
          <FileArchive className="w-12 h-12 text-white" />
        </div>
        {landed && (
          <>
            <span className="absolute -top-2 -right-2 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--success)] opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-[var(--success)]" />
            </span>
            <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 h-2 w-16 rounded-full bg-black/30 blur-sm animate-scale-in" />
          </>
        )}
      </div>
      <p className="mt-7 text-sm text-white/70 font-mono animate-scale-in">banking-core.zip — 1,284 files</p>
    </div>
  );
}

function ScanStage() {
  const percent = useCountUp(100, true, 2200);
  const bars = ['w-4/5', 'w-3/5', 'w-11/12', 'w-2/3', 'w-9/12'];
  return (
    <div className="flex flex-col items-center">
      <div className="flex items-center gap-4">
        <div className="relative w-24 h-24">
          <div className="absolute inset-0 rounded-full border border-white/15 animate-spin-slow" />
          <div className="absolute inset-3 rounded-full border-2 border-dashed border-[var(--accent-purple)]/60 animate-spin-slow" style={{ animationDirection: 'reverse' }} />
          <div className="absolute inset-0 flex items-center justify-center">
            <Cpu className="w-7 h-7 text-white" />
          </div>
        </div>
        <div>
          <div className="text-4xl font-bold text-white tabular-nums">{percent}%</div>
          <div className="text-[11px] text-white/60">extracted</div>
        </div>
      </div>

      <div className="relative mt-6 w-64 overflow-hidden rounded-xl border border-white/15 bg-black/25 p-3">
        <div className="space-y-2">
          {bars.map((w, i) => (
            <div key={i} className={cn('h-1.5 rounded-full bg-white/20', w)} />
          ))}
        </div>
        <div className="absolute inset-x-0 h-6 bg-gradient-to-b from-transparent via-[var(--accent-blue)]/35 to-transparent animate-scan-sweep" />
        <div className="absolute left-0 right-0 top-0 h-px bg-[var(--accent-blue)]/80 animate-scan-sweep" />
      </div>
      <p className="mt-4 text-xs text-white/60 font-mono animate-scale-in">classes 1,284 · methods 9,412 · deps 3,720</p>
    </div>
  );
}

function GeneratedStage() {
  const confetti = useMemo(
    () =>
      Array.from({ length: 16 }, (_, i) => ({
        left: 8 + ((i * 53) % 84),
        delay: `${(i % 8) * 0.06}s`,
        color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
        rotate: (i * 37) % 360,
      })),
    []
  );
  const services = ['Payments', 'Ledger', 'Users', 'Orders', 'Inventory', 'Billing'];
  return (
    <div className="relative flex flex-col items-center">
      <div className="relative">
        <span className="absolute -inset-6 rounded-full bg-[var(--success)]/20 blur-2xl animate-pulse-soft" />
        <div className="relative w-24 h-24 rounded-2xl bg-gradient-to-br from-[var(--success)]/90 to-emerald-700 flex items-center justify-center animate-pop shadow-2xl">
          <PartyPopper className="w-11 h-11 text-white" />
        </div>
        <span className="absolute inset-0 rounded-2xl ring-2 ring-[var(--success)]/40 animate-ring" />
      </div>

      {confetti.map((c, i) => (
        <span
          key={i}
          style={{ left: `${c.left}%`, top: '55%', animationDelay: c.delay, backgroundColor: c.color, transform: `rotate(${c.rotate}deg)` }}
          className="absolute w-1.5 h-2.5 rounded-sm animate-burst pointer-events-none"
        />
      ))}

      <div className="relative mt-8 grid grid-cols-3 gap-2">
        {services.map((s, i) => (
          <div
            key={s}
            style={{ animationDelay: `${0.1 + i * 0.07}s` }}
            className="animate-pop rounded-xl bg-white/10 backdrop-blur border border-white/20 px-3 py-2 text-center"
          >
            <Network className="w-4 h-4 mx-auto text-[var(--accent-purple)]" />
            <p className="mt-1 text-[11px] text-white/85 font-medium">{s}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

const AWS_SERVICES = [
  { label: 'Lambda', icon: Zap, color: 'text-amber-300' },
  { label: 'API Gateway', icon: Waypoints, color: 'text-indigo-300' },
  { label: 'S3', icon: HardDrive, color: 'text-emerald-300' },
  { label: 'DynamoDB', icon: Database, color: 'text-sky-300' },
  { label: 'SQS', icon: MessageSquare, color: 'text-rose-300' },
  { label: 'EventBridge', icon: Activity, color: 'text-fuchsia-300' },
];

function AwsStage() {
  return (
    <div className="relative flex flex-col items-center">
      <div className="relative">
        <span className="absolute -inset-5 rounded-full bg-[var(--accent-blue)]/25 blur-2xl animate-pulse-soft" />
        <div className="relative w-24 h-24 rounded-2xl bg-gradient-to-br from-[var(--accent-blue)] to-[var(--accent-purple)] flex items-center justify-center animate-float-slow shadow-2xl">
          <Cloud className="w-11 h-11 text-white" />
        </div>
      </div>
      <div className="relative mt-8 grid grid-cols-3 gap-2">
        {AWS_SERVICES.map((svc, i) => {
          const Icon = svc.icon;
          return (
            <div
              key={svc.label}
              style={{ animationDelay: `${0.1 + i * 0.07}s` }}
              className="animate-pop flex items-center gap-1.5 rounded-xl bg-white/10 backdrop-blur border border-white/20 px-3 py-2"
            >
              <Icon className={cn('w-4 h-4', svc.color)} />
              <span className="text-[11px] text-white/85 font-medium">{svc.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

type NodeDef = { id: string; label: string; x: number; y: number };

const WEB_NODES: NodeDef[] = [
  { id: 'gateway', label: 'Gateway', x: 170, y: 130 },
  { id: 'payments', label: 'Payments', x: 170, y: 14 },
  { id: 'ledger', label: 'Ledger', x: 284, y: 48 },
  { id: 'orders', label: 'Orders', x: 310, y: 130 },
  { id: 'inventory', label: 'Inventory', x: 284, y: 212 },
  { id: 'analytics', label: 'Analytics', x: 170, y: 246 },
  { id: 'billing', label: 'Billing', x: 56, y: 212 },
  { id: 'users', label: 'Users', x: 30, y: 130 },
  { id: 'notifications', label: 'Notify', x: 56, y: 48 },
];

const EDGES: [string, string][] = [
  ['gateway', 'payments'],
  ['gateway', 'ledger'],
  ['gateway', 'orders'],
  ['gateway', 'inventory'],
  ['gateway', 'analytics'],
  ['gateway', 'billing'],
  ['gateway', 'users'],
  ['gateway', 'notifications'],
  ['payments', 'ledger'],
  ['ledger', 'orders'],
  ['orders', 'inventory'],
  ['inventory', 'analytics'],
  ['analytics', 'billing'],
  ['billing', 'users'],
  ['users', 'notifications'],
  ['notifications', 'payments'],
];

function WebStage() {
  const byId = useMemo(() => Object.fromEntries(WEB_NODES.map((n) => [n.id, n])), []);
  return (
    <div className="relative w-[340px] h-[270px]">
      <svg viewBox="0 0 340 270" className="absolute inset-0 h-full w-full">
        {EDGES.map(([a, b], i) => {
          const na = byId[a];
          const nb = byId[b];
          return (
            <g key={`${a}-${b}`}>
              <line
                x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
                stroke="rgba(255,255,255,0.18)"
                strokeWidth="1"
                strokeDasharray="300"
                className="animate-dash-in"
                style={{ animationDelay: `${i * 0.06}s` }}
              />
              <line
                x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
                stroke="rgba(129,140,248,0.55)"
                strokeWidth="1.4"
                strokeDasharray="4 10"
                strokeLinecap="round"
                className="animate-dash-flow"
                style={{ animationDelay: `${0.8 + i * 0.04}s` }}
              />
            </g>
          );
        })}
      </svg>

      {WEB_NODES.map((node, i) => {
        const isCenter = node.id === 'gateway';
        return (
          <div
            key={node.id}
            style={{
              left: `${(node.x / 340) * 100}%`,
              top: `${(node.y / 270) * 100}%`,
              animationDelay: `${isCenter ? 0 : 0.25 + i * 0.05}s`,
              transform: 'translate(-50%, -50%)',
            }}
            className="absolute -translate-x-1/2 -translate-y-1/2 animate-pop"
          >
            {isCenter && (
              <span className="absolute -inset-3 rounded-full ring-2 ring-[var(--accent-purple)]/50 animate-ring" />
            )}
            <div
              className={cn(
                'flex items-center justify-center rounded-xl border shadow-lg backdrop-blur',
                isCenter
                  ? 'h-12 w-12 bg-gradient-to-br from-[var(--accent-blue)] to-[var(--accent-purple)] border-white/30'
                  : 'h-8 w-16 bg-white/10 border-white/20'
              )}
            >
              {isCenter ? (
                <Network className="w-5 h-5 text-white" />
              ) : (
                <span className="text-[9px] text-white/90 font-medium truncate px-1">{node.label}</span>
              )}
            </div>
            {!isCenter && (
              <div className="absolute left-1/2 -bottom-1.5 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-[var(--accent-blue)] animate-ping" style={{ animationDelay: `${i * 0.15}s` }} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function SceneStage({ id }: { id: SceneId }) {
  switch (id) {
    case 'drop':
      return <DropStage />;
    case 'scan':
      return <ScanStage />;
    case 'generated':
      return <GeneratedStage />;
    case 'aws':
      return <AwsStage />;
    case 'web':
      return <WebStage />;
  }
}

export function AuthShowcase() {
  const [index, setIndex] = useState(0);
  const scene = useMemo(() => SCENES[index % SCENES.length], [index]);
  const activeStep = STEP_INDEX[scene.id];

  useEffect(() => {
    const timer = setTimeout(() => setIndex((i) => i + 1), scene.duration);
    return () => clearTimeout(timer);
  }, [scene.id, scene.duration]);

  return (
    <div className="relative flex h-full min-h-[560px] flex-col overflow-hidden bg-gradient-to-br from-[#1E1B4B] via-[#312E81] to-[#0B1220] text-white">
      <div className="absolute -top-24 -left-24 w-96 h-96 rounded-full bg-[var(--accent-purple)]/25 blur-3xl" />
      <div className="absolute -bottom-32 -right-24 w-[28rem] h-[28rem] rounded-full bg-[var(--accent-blue)]/20 blur-3xl" />
      <div className="absolute top-1/3 right-0 w-40 h-40 rounded-full bg-[var(--accent-purple)]/15 blur-2xl" />
      <div className="absolute inset-0 opacity-[0.15] [background-image:radial-gradient(rgba(255,255,255,0.35)_1px,transparent_1px)] [background-size:22px_22px]" />

      <div className="relative z-10 flex items-center justify-between px-10 pt-8">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-[var(--accent-blue)] to-[var(--accent-purple)] flex items-center justify-center shadow-lg">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="text-sm font-bold leading-tight">EMIP</p>
            <p className="text-[10px] text-white/60 leading-tight">Modernization Intelligence</p>
          </div>
        </div>
        <span className="rounded-full border border-white/15 bg-white/5 px-2.5 py-1 text-[10px] text-white/70">
          Monolith → Microservices → Cloud
        </span>
      </div>

      <div className="relative z-10 flex-1 flex items-center justify-center px-8">
        <div key={scene.id} className="animate-fade-up flex flex-col items-center text-center w-full">
          <SceneStage id={scene.id} />
          <h2 className="mt-8 text-2xl font-bold tracking-tight">{scene.title}</h2>
          <p className="mt-2 max-w-sm text-sm text-white/70">{scene.quote}</p>
        </div>
      </div>

      <div className="relative z-10 flex flex-col items-center gap-4 pb-8">
        <div className="flex items-center gap-2">
          {STEPS.map((step, i) => {
            const StepIcon = step.icon;
            const active = i === activeStep;
            return (
              <div key={step.label} className="flex items-center gap-2">
                <div
                  className={cn(
                    'flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-medium transition-all',
                    active
                      ? 'border-white/30 bg-white/15 text-white'
                      : 'border-white/10 bg-white/5 text-white/50'
                  )}
                >
                  <StepIcon className={cn('w-3.5 h-3.5', active && 'text-[var(--accent-purple)]')} />
                  {step.label}
                </div>
                {i < STEPS.length - 1 && <div className="w-5 h-px bg-white/20" />}
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-1.5">
          {SCENES.map((s, i) => (
            <button
              key={s.id}
              onClick={() => setIndex(i)}
              aria-label={`Show scene: ${s.title}`}
              className={cn(
                'h-1.5 rounded-full transition-all',
                i === index ? 'w-6 bg-white' : 'w-1.5 bg-white/30 hover:bg-white/50'
              )}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
