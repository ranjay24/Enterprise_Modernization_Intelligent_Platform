import { useState, useMemo } from 'react';
import { ArrowUpDown, Search } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { ServiceReadiness } from '@/types/dashboard';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { ConfidenceBadge, StatusBadge } from '@/components/ui/StatusBadge';
import { Input } from '@/components/ui/Input';

type SortKey = 'name' | 'readiness' | 'risk' | 'confidence' | 'cohesion' | 'coupling' | 'classes';

const readinessDot: Record<string, string> = {
  green: 'bg-success',
  yellow: 'bg-warning',
  red: 'bg-danger',
};

const riskColor: Record<string, string> = {
  low: 'text-success',
  medium: 'text-warning',
  high: 'text-danger',
};

export function ServiceReadinessMatrix({ services }: { services: ServiceReadiness[] }) {
  const [sortKey, setSortKey] = useState<SortKey>('confidence');
  const [sortAsc, setSortAsc] = useState(false);
  const [search, setSearch] = useState('');

  const sorted = useMemo(() => {
    let filtered = services;
    if (search) {
      const q = search.toLowerCase();
      filtered = services.filter(s => s.name.toLowerCase().includes(q));
    }
    return [...filtered].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return sortAsc ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
    });
  }, [services, sortKey, sortAsc, search]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  };

  const SortHeader = ({ label, sortId }: { label: string; sortId: SortKey }) => (
    <th
      className="text-left py-3 px-3 font-medium text-muted-foreground cursor-pointer hover:text-foreground select-none text-[11px] uppercase tracking-wider"
      onClick={() => toggleSort(sortId)}
    >
      <span className="flex items-center gap-1">
        {label}
        <ArrowUpDown className={cn('w-3 h-3', sortKey === sortId && 'text-primary')} />
      </span>
    </th>
  );

  return (
    <section>
      <SectionHeader
        title="Service Readiness Matrix"
        description="Service-level readiness assessment"
        size="lg"
        action={
          <Input
            placeholder="Filter services..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-48"
            icon={<Search className="w-3.5 h-3.5" />}
          />
        }
      />
      <div className="bg-card rounded-xl border overflow-hidden mt-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/30">
                <SortHeader label="Service" sortId="name" />
                <SortHeader label="Ready" sortId="readiness" />
                <SortHeader label="Risk" sortId="risk" />
                <SortHeader label="Confidence" sortId="confidence" />
                <SortHeader label="Cohesion" sortId="cohesion" />
                <SortHeader label="Coupling" sortId="coupling" />
                <SortHeader label="Classes" sortId="classes" />
                <th className="text-left py-3 px-3 font-medium text-muted-foreground text-[11px] uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((svc, idx) => (
                <tr
                  key={svc.id}
                  className={cn(
                    'border-b last:border-0 hover:bg-accent/50 transition-colors',
                    idx % 2 === 0 && 'bg-card',
                    idx % 2 === 1 && 'bg-muted/20',
                  )}
                >
                  <td className="py-3 px-3 font-medium text-foreground text-sm">{svc.name}</td>
                  <td className="py-3 px-3">
                    <span className={cn('w-2.5 h-2.5 rounded-full inline-block', readinessDot[svc.readiness])} />
                  </td>
                  <td className="py-3 px-3">
                    <span className={cn('text-xs font-semibold', riskColor[svc.risk])}>{svc.risk}</span>
                  </td>
                  <td className="py-3 px-3"><ConfidenceBadge value={svc.confidence} /></td>
                  <td className="py-3 px-3 text-foreground text-sm tabular-nums">{svc.cohesion}%</td>
                  <td className="py-3 px-3 text-foreground text-sm tabular-nums">{svc.coupling}%</td>
                  <td className="py-3 px-3 text-foreground text-sm tabular-nums">{svc.classes}</td>
                  <td className="py-3 px-3"><StatusBadge status={svc.status} /></td>
                </tr>
              ))}
              {sorted.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-sm text-muted-foreground">No services match filter</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
