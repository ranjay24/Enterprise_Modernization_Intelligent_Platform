import { CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';
import { cn } from '@/utils/cn';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { Badge } from '@/components/ui/Badge';
import type { ValidationCheckpoint } from '@/types/results';

const statusConfig = {
  pass: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50 dark:bg-green-900/20', border: 'border-green-200 dark:border-green-800/30', badge: 'success' as const },
  fail: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-50 dark:bg-red-900/20', border: 'border-red-200 dark:border-red-800/30', badge: 'destructive' as const },
  pending: { icon: Clock, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-200 dark:border-blue-800/30', badge: 'outline' as const },
  warning: { icon: AlertTriangle, color: 'text-yellow-600', bg: 'bg-yellow-50 dark:bg-yellow-900/20', border: 'border-yellow-200 dark:border-yellow-800/30', badge: 'warning' as const },
};

export function ValidationSummary({ checkpoints }: { checkpoints: ValidationCheckpoint[] }) {
  const passed = checkpoints.filter((c) => c.status === 'pass').length;
  const total = checkpoints.length;
  const allPassed = passed === total;

  return (
    <section>
      <SectionHeader
        title="Validation Summary"
        description={`Analysis pipeline health — ${passed}/${total} checks passed`}
        action={
          <Badge variant={allPassed ? 'success' : 'warning'}>
            {allPassed ? 'All Passed' : `${total - passed} Pending`}
          </Badge>
        }
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {checkpoints.map((cp) => {
          const cfg = statusConfig[cp.status];
          const Icon = cfg.icon;
          return (
            <article
              key={cp.id}
              className={cn('rounded-xl border p-4 transition-all hover:shadow-md', cfg.bg, cfg.border)}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Icon className={cn('w-5 h-5', cfg.color)} />
                  <h3 className="text-sm font-semibold text-foreground">{cp.name}</h3>
                </div>
                <Badge variant={cfg.badge}>
                  {cp.status === 'pass' ? 'PASS' : cp.status === 'fail' ? 'FAIL' : cp.status === 'pending' ? 'PENDING' : 'WARN'}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">{cp.message}</p>
              {cp.timestamp && (
                <p className="text-xs text-muted-foreground mt-1 opacity-70">
                  {new Date(cp.timestamp).toLocaleString()}
                </p>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
