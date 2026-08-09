import { AlertOctagon, Zap, XCircle } from 'lucide-react';
import { cn } from '@/utils/cn';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { DebtCard } from '@/components/cards/DebtCard';
import { Badge } from '@/components/ui/Badge';
import type { AnalysisResult } from '@/types/api';
import type { DebtItem } from '@/types/dashboard';
import type { GodClassMetric, CircularDependencyMetric, DeadCodeMetric } from '@/types/metrics';

function buildDebtItems(analysis: AnalysisResult): DebtItem[] {
  const godClasses = (analysis.metrics?.god_classes || []) as GodClassMetric[];
  const circularDeps = (analysis.metrics?.circular_dependencies || []) as CircularDependencyMetric[];
  const deadCode = (analysis.metrics?.dead_code || []) as DeadCodeMetric[];
  const items: DebtItem[] = [];

  if (godClasses.length > 0) {
    items.push({
      id: 'debt-god', category: 'God Classes', count: godClasses.length,
      severity: 'critical', icon: 'AlertOctagon',
      description: `${godClasses.length} classes exceeding complexity thresholds`,
      recommendation: 'Decompose into smaller, focused services with clear boundaries',
    });
  }
  if (circularDeps.length > 0) {
    items.push({
      id: 'debt-circular', category: 'Circular Dependencies', count: circularDeps.length,
      severity: 'high', icon: 'Zap',
      description: `${circularDeps.length} import/injection cycles detected`,
      recommendation: 'Break cycles using event-driven patterns or dependency inversion',
    });
  }
  if (deadCode.length > 0) {
    items.push({
      id: 'debt-dead', category: 'Dead Code', count: deadCode.length,
      severity: 'medium', icon: 'Trash2',
      description: `${deadCode.length} unreferenced classes found`,
      recommendation: 'Remove dead code to reduce maintenance burden and improve clarity',
    });
  }
  return items;
}

export function TechnicalDebtCenter({ analysis }: { analysis: AnalysisResult }) {
  const debtItems = buildDebtItems(analysis);
  const godClasses = (analysis.metrics?.god_classes || []) as GodClassMetric[];
  const circularDeps = (analysis.metrics?.circular_dependencies || []) as CircularDependencyMetric[];
  const deadCode = (analysis.metrics?.dead_code || []) as DeadCodeMetric[];
  const totalDebt = godClasses.length + circularDeps.length + deadCode.length;

  return (
    <section>
      <SectionHeader
        title="Technical Debt Center"
        description={`${totalDebt} debt items identified`}
        action={
          totalDebt > 0 ? (
            <Badge variant="destructive">{totalDebt} items</Badge>
          ) : (
            <Badge variant="success">Clean</Badge>
          )
        }
      />

      {totalDebt === 0 ? (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800/30 rounded-xl p-6 text-center">
          <AlertOctagon className="w-12 h-12 text-green-500 mx-auto mb-3" />
          <h3 className="font-semibold text-green-800 dark:text-green-300 mb-1">No Major Technical Debt Detected</h3>
          <p className="text-sm text-green-600 dark:text-green-400">The codebase appears well-structured.</p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {debtItems.map((item) => (
              <DebtCard key={item.id} data={item} />
            ))}
          </div>

          {godClasses.length > 0 && (
            <div className="bg-card rounded-xl border p-5">
              <h3 className="font-semibold text-foreground text-sm mb-3 flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-red-500" /> God Classes Detail
              </h3>
              <div className="space-y-2">
                {godClasses.map((gc: GodClassMetric, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-100 dark:border-red-800/30">
                    <div>
                      <span className="font-medium text-red-800 dark:text-red-300">{gc.name}</span>
                      <span className="text-xs text-red-600 dark:text-red-400 ml-2">({gc.package})</span>
                    </div>
                    <div className="text-sm text-red-600 dark:text-red-400">
                      {gc.lines_of_code} LOC, {gc.method_count} methods
                      {gc.injected_dependencies > 0 && `, ${gc.injected_dependencies} deps`}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {circularDeps.length > 0 && (
            <div className="bg-card rounded-xl border p-5">
              <h3 className="font-semibold text-foreground text-sm mb-3 flex items-center gap-2">
                <Zap className="w-4 h-4 text-yellow-500" /> Circular Dependencies Detail
              </h3>
              <div className="space-y-2">
                {circularDeps.map((cd: CircularDependencyMetric, i: number) => (
                  <div key={i} className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-100 dark:border-yellow-800/30">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-yellow-800 dark:text-yellow-300">{cd.type} cycle</span>
                      <span className="text-xs text-yellow-600 dark:text-yellow-400">{cd.cycle?.length || 0} classes</span>
                    </div>
                    <div className="text-sm text-yellow-700 dark:text-yellow-400 mt-1">{cd.cycle?.join(' → ') || 'Unknown cycle'}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {deadCode.length > 0 && (
            <div className="bg-card rounded-xl border p-5">
              <h3 className="font-semibold text-foreground text-sm mb-3 flex items-center gap-2">
                <XCircle className="w-4 h-4 text-muted-foreground" /> Dead Code Detail
              </h3>
              <div className="space-y-2">
                {deadCode.map((dc: DeadCodeMetric, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                    <div>
                      <span className="font-medium text-foreground">{dc.name}</span>
                      <span className="text-xs text-muted-foreground ml-2">({dc.package})</span>
                    </div>
                    <span className="text-sm text-muted-foreground">{dc.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
