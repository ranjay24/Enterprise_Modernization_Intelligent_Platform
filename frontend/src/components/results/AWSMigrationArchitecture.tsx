import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  Box,
  Cloud,
  Database,
  Layers,
  Lock,
  Package,
  Radio,
  Route,
  X,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import type { AWSServiceRecommendation, MigrationWave, ServiceBoundary } from '@/types/api';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/utils/cn';
import { buildAwsInventory, awsCategory } from '@/utils/awsInventory';

type AwsCategory =
  | 'gateway'
  | 'compute'
  | 'database'
  | 'messaging'
  | 'observability'
  | 'storage'
  | 'security'
  | 'other';

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

interface AWSMigrationArchitectureProps {
  waves: MigrationWave[];
  services: ServiceBoundary[];
}

export function AWSMigrationArchitecture({ waves, services }: AWSMigrationArchitectureProps) {
  const firstWave = waves[0];
  const [selectedWaveNumber, setSelectedWaveNumber] = useState<number | null>(firstWave?.wave_number ?? null);
  const [selectedService, setSelectedService] = useState<string | null>(firstWave?.services?.[0] ?? null);
  const [detailService, setDetailService] = useState<string | null>(null);

  const selectedWave = waves.find((w) => w.wave_number === selectedWaveNumber) ?? null;
  const waveServices = selectedWave?.services ?? [];
  const selectedRecs = selectedWave?.aws_recommendations?.[selectedService ?? ''] ?? [];

  const uniqueServices = useMemo(() => new Set(waves.flatMap((w) => w.services ?? [])).size, [waves]);
  const uniqueAwsServices = useMemo(
    () =>
      new Set(
        waves.flatMap((w) =>
          Object.values(w.aws_recommendations ?? {}).flatMap((recs) => recs.map((r) => r.service_name))
        )
      ).size,
    [waves]
  );
  const inventory = useMemo(() => buildAwsInventory(waves), [waves]);
  const inventoryCategories = Array.from(new Set(inventory.map((e) => e.category)));

  const selectWave = (w: MigrationWave) => {
    setSelectedWaveNumber(w.wave_number);
    setSelectedService(w.services?.[0] ?? null);
  };

  const selectService = (name: string) => {
    setSelectedService(name);
    setDetailService(name);
  };

  if (waves.length === 0) return null;

  // Get all unique services with their indices
  const allServices = Array.from(new Set(waves.flatMap((w) => w.services ?? [])));
  const serviceIndex: Record<string, number> = {};
  allServices.forEach((svc, idx) => {
    serviceIndex[svc] = idx + 1;
  });

  return (
    <div className="space-y-6">
      {/* Title & Description */}
      <div>
        <h1 className="text-3xl font-bold text-[var(--text-primary)]">AWS Migration</h1>
        <p className="text-sm text-[var(--text-secondary)] mt-1">
          Target AWS deployment blueprint across {uniqueServices} services and {waves.length} waves ({uniqueAwsServices} managed services)
        </p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-3 flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-[var(--accent-purple)]" />
            <span className="text-2xl font-bold text-[var(--text-primary)]">{waves.length}</span>
          </div>
          <span className="text-xs text-[var(--text-secondary)]">Total Waves</span>
        </div>
        <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-3 flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Box className="w-5 h-5 text-[var(--architecture)]" />
            <span className="text-2xl font-bold text-[var(--text-primary)]">{uniqueServices}</span>
          </div>
          <span className="text-xs text-[var(--text-secondary)]">Total Services</span>
        </div>
        <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-3 flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Cloud className="w-5 h-5 text-[var(--accent-blue)]" />
            <span className="text-2xl font-bold text-[var(--text-primary)]">{uniqueAwsServices}</span>
          </div>
          <span className="text-xs text-[var(--text-secondary)]">Managed Services</span>
        </div>
      </div>

      {/* Section Labels */}
      <div className="grid grid-cols-3 gap-4 text-center">
        <h3 className="text-sm font-semibold text-[var(--accent-purple)]">1. Migration Waves</h3>
        <h3 className="text-sm font-semibold text-[var(--architecture)]">2. Microservices</h3>
        <h3 className="text-sm font-semibold text-[var(--accent-blue)]">3. AWS Target Services</h3>
      </div>

      {/* Main Architecture Diagram */}
      <div className="relative rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-base)] p-6 overflow-auto">
        <div className="grid grid-cols-3 gap-8 min-w-max">
          {/* Column 1: Migration Waves */}
          <div className="space-y-3 flex flex-col">
            {waves.map((w) => (
              <button
                key={w.wave_number}
                onClick={() => selectWave(w)}
                className={cn(
                  'text-left rounded-lg border-2 p-3 transition-all cursor-pointer hover:shadow-md',
                  selectedWaveNumber === w.wave_number
                    ? 'border-[var(--accent-purple)] bg-[var(--accent-purple)]/5'
                    : 'border-[var(--border-subtle)] bg-[var(--bg-card)] hover:border-[var(--accent-purple)]/50'
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <Layers className="w-4 h-4 text-[var(--accent-purple)]" />
                  <span className="font-semibold text-sm text-[var(--text-primary)]">W{w.wave_number}</span>
                </div>
                <p className="text-xs text-[var(--text-secondary)] mb-2">{w.name}</p>
                <div className="text-[10px] text-[var(--text-muted)]">
                  <div>{w.services?.length ?? 0} Services</div>
                </div>
              </button>
            ))}
          </div>

          {/* Column 2: Microservices */}
          <div className="space-y-3 flex flex-col">
            {waveServices.map((name) => {
              const boundary = services.find((s) => s.name === name);
              const idx = serviceIndex[name];
              const active = name === selectedService;
              return (
                <button
                  key={name}
                  onClick={() => selectService(name)}
                  className={cn(
                    'text-left rounded-lg border-2 p-3 transition-all cursor-pointer hover:shadow-md flex gap-2',
                    active
                      ? 'border-[var(--architecture)] bg-[var(--architecture)]/5'
                      : 'border-[var(--border-subtle)] bg-[var(--bg-card)] hover:border-[var(--architecture)]/50'
                  )}
                >
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-[var(--architecture)] text-white flex items-center justify-center text-xs font-bold">
                    {idx}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-sm text-[var(--text-primary)] truncate">{name}</p>
                    {boundary?.business_capability && (
                      <p className="text-xs text-[var(--text-secondary)] truncate">{boundary.business_capability}</p>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Column 3: AWS Target Services */}
          <div className="space-y-3 flex flex-col">
            {selectedService && selectedRecs.length > 0 ? (
              selectedRecs.map((rec) => {
                const cat = CATS[awsCategory(rec.service_name)];
                const Icon = cat.icon;
                return (
                  <div
                    key={rec.service_name}
                    className="rounded-lg border-2 p-3 cursor-pointer transition-all hover:shadow-md"
                    style={{ borderColor: cat.color, backgroundColor: `${cat.color}10` }}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className="w-4 h-4" style={{ color: cat.color }} />
                      <span className="font-semibold text-sm text-[var(--text-primary)] truncate">{rec.service_name}</span>
                    </div>
                    <p className="text-xs text-[var(--text-secondary)] mb-1">{rec.use_case}</p>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-8 text-xs text-[var(--text-muted)]">
                Select a microservice to view AWS services
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)] mb-3">Legend (AWS Categories)</h4>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {Object.entries(CATS).map(([key, cat]) => (
            <div key={key} className="flex items-center gap-2">
              <div className="w-4 h-0.5 rounded-full" style={{ backgroundColor: cat.color }} />
              <span className="text-xs text-[var(--text-secondary)] capitalize">{key}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Full AWS resource inventory */}
      {inventory.length > 0 && (
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-5">
          <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
            <div>
              <h4 className="text-sm font-semibold text-[var(--text-primary)]">AWS Resource Inventory</h4>
              <p className="text-[11px] text-[var(--text-secondary)]">Every AWS service identified across the migration plan, grouped by category</p>
            </div>
            <div className="flex items-center gap-2">
              {inventoryCategories.map((cat) => (
                <span key={cat} className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: CATS[cat].color }} />
                  {cat}
                </span>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {inventory.map((entry) => {
              const cat = CATS[entry.category];
              const Icon = cat.icon;
              return (
                <div
                  key={entry.service_name}
                  className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] p-3.5"
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
                  <div className="flex flex-wrap gap-1">
                    {entry.waves.map((w) => (
                      <span key={w} className="px-1.5 py-0.5 rounded bg-[var(--border-subtle)] text-[10px] text-[var(--text-muted)]">W{w}</span>
                    ))}
                    <span className="text-[10px] text-[var(--text-muted)] leading-5">
                      {entry.microservices.join(', ')}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Right sidebar — service details */}
      <ServiceDetailsDrawer
        serviceName={detailService}
        waveNumber={detailService ? waveNumberForService(waves, detailService) : null}
        boundary={serviceDetailFor(services, detailService)}
        recs={detailService ? recsForService(waves, detailService) : []}
        onClose={() => setDetailService(null)}
      />
    </div>
  );
}

interface ServiceDetailsDrawerProps {
  serviceName: string | null;
  waveNumber: number | null;
  boundary: ServiceBoundary | null;
  recs: AWSServiceRecommendation[];
  onClose: () => void;
}

function ServiceDetailsDrawer({ serviceName, waveNumber, boundary, recs, onClose }: ServiceDetailsDrawerProps) {
  useEffect(() => {
    if (!serviceName) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [serviceName, onClose]);

  return (
    <AnimatePresence>
      {serviceName && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
            onClick={onClose}
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 220 }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-[var(--bg-card)] border-l border-[var(--border-subtle)] z-50 overflow-y-auto"
          >
            <div className="sticky top-0 bg-[var(--bg-card)] border-b border-[var(--border-subtle)] p-4 flex items-center justify-between z-10">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h2 className="font-semibold text-[var(--text-primary)] truncate">{serviceName}</h2>
                  {waveNumber != null && <Badge variant="neutral" size="sm">Wave {waveNumber}</Badge>}
                </div>
                {boundary?.business_capability && (
                  <p className="text-xs text-[var(--text-secondary)] mt-0.5">{boundary.business_capability}</p>
                )}
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-5">
              {boundary?.description && (
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)] mb-1.5">Description</h3>
                  <p className="text-sm text-[var(--text-secondary)]">{boundary.description}</p>
                </div>
              )}

              {boundary && (
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)] mb-2">Service Details</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="bg-[var(--border-subtle)]/40 rounded-lg p-3">
                      <p className="text-xs text-[var(--text-muted)]">APIs</p>
                      <p className="font-semibold text-[var(--text-primary)] mt-0.5">{boundary.api_endpoints?.length ?? 0}</p>
                    </div>
                    <div className="bg-[var(--border-subtle)]/40 rounded-lg p-3">
                      <p className="text-xs text-[var(--text-muted)]">DB Tables</p>
                      <p className="font-semibold text-[var(--text-primary)] mt-0.5">{boundary.database_tables?.length ?? 0}</p>
                    </div>
                  </div>
                </div>
              )}

              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)] mb-2">
                  AWS Recommendations {recs.length > 0 && <span className="text-[var(--text-muted)]">· {recs.length}</span>}
                </h3>
                {recs.length === 0 ? (
                  <p className="text-sm text-[var(--text-muted)]">No recommendations available.</p>
                ) : (
                  <div className="space-y-2.5">
                    {recs.map((rec) => {
                      const cat = CATS[awsCategory(rec.service_name)];
                      const Icon = cat.icon;
                      return (
                        <div key={rec.service_name} className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] p-3">
                          <div className="flex items-center gap-2 mb-1">
                            <Icon className="w-4 h-4" style={{ color: cat.color }} />
                            <span className="text-sm font-semibold text-[var(--text-primary)]">{rec.service_name}</span>
                          </div>
                          <p className="text-xs font-medium text-[var(--accent-blue)] mb-1">{rec.use_case}</p>
                          <p className="text-xs text-[var(--text-secondary)]">{rec.justification}</p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function waveNumberForService(waves: MigrationWave[], name: string): number | null {
  const w = waves.find((wave) => (wave.services ?? []).includes(name));
  return w?.wave_number ?? null;
}

function serviceDetailFor(services: ServiceBoundary[], name: string | null): ServiceBoundary | null {
  if (!name) return null;
  return services.find((s) => s.name === name) ?? null;
}

function recsForService(waves: MigrationWave[], name: string): AWSServiceRecommendation[] {
  const w = waves.find((wave) => (wave.services ?? []).includes(name));
  return w?.aws_recommendations?.[name] ?? [];
}
