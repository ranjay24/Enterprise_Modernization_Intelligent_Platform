import { Link } from 'react-router-dom';
import type { RecentAnalysis } from '@/types/dashboard';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Button } from '@/components/ui/Button';
import { cn } from '@/utils/cn';
import { Eye } from 'lucide-react';

export function RecentAnalyses({ data }: { data: RecentAnalysis[] }) {
  return (
    <section>
      <SectionHeader title="Recent Analyses" description="Previous analysis jobs and their status" size="lg" />
      <div className="bg-card rounded-xl border overflow-hidden mt-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/30">
                {['Project', 'Date', 'Status', 'Readiness', 'Risk', 'Services', ''].map((h) => (
                  <th key={h} className="text-left py-3 px-4 font-medium text-muted-foreground text-[11px] uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((item, idx) => (
                <tr
                  key={item.id}
                  className={cn(
                    'border-b last:border-0 hover:bg-accent/50 transition-colors',
                    idx % 2 === 0 && 'bg-card',
                    idx % 2 === 1 && 'bg-muted/20',
                  )}
                >
                  <td className="py-3 px-4 font-medium text-foreground">{item.projectName}</td>
                  <td className="py-3 px-4 text-muted-foreground text-xs">{new Date(item.date).toLocaleDateString()}</td>
                  <td className="py-3 px-4"><StatusBadge status={item.status} /></td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
                        <div className={cn(
                          'h-full rounded-full',
                          item.status === 'completed'
                            ? item.readiness >= 70 ? 'bg-success' : item.readiness >= 40 ? 'bg-warning' : 'bg-danger'
                            : 'bg-muted-foreground/20'
                        )} style={{ width: `${item.readiness}%` }} />
                      </div>
                      <span className="text-xs text-muted-foreground tabular-nums w-7 text-right">
                        {item.status === 'completed' ? `${item.readiness}%` : '-'}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    {item.status === 'completed' ? (
                      <span className={cn(
                        'text-xs font-semibold',
                        item.risk === 'low' ? 'text-success' : item.risk === 'medium' ? 'text-warning' : 'text-danger'
                      )}>{item.risk}</span>
                    ) : <span className="text-xs text-muted-foreground">-</span>}
                  </td>
                  <td className="py-3 px-4 text-muted-foreground text-xs">{item.services || '-'}</td>
                  <td className="py-3 px-4">
                    {item.status === 'completed' ? (
                      <Link to={`/jobs/${item.id}/results`}>
                        <Button variant="ghost" size="sm" className="gap-1.5">
                          <Eye className="w-3.5 h-3.5" />
                          View
                        </Button>
                      </Link>
                    ) : null}
                  </td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-sm text-muted-foreground">No analyses yet</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
