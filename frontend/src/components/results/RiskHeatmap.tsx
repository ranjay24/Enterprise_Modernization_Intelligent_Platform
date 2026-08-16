import { cn } from '@/utils/cn';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { Badge } from '@/components/ui/Badge';
import type { RiskHeatmapEntry } from '@/types/results';

const riskColors = {
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

const cellColors = {
  low: 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400',
  medium: 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400',
  high: 'bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-400',
  critical: 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400',
};

function RiskCell({ level }: { level: string }) {
  const risk = level as keyof typeof cellColors;
  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded text-xs font-medium', cellColors[risk] || cellColors.low)}>
      {level.charAt(0).toUpperCase() + level.slice(1)}
    </span>
  );
}

export function RiskHeatmap({ entries }: { entries: RiskHeatmapEntry[] }) {
  const criticalCount = entries.filter((e) => e.overallRisk === 'critical').length;
  const highCount = entries.filter((e) => e.overallRisk === 'high').length;

  return (
    <section>
      <SectionHeader
        title="Risk Heatmap"
        description="Multi-dimensional risk assessment per service"
        action={
          <div className="flex items-center gap-2">
            {criticalCount > 0 && (
              <Badge variant="destructive">{criticalCount} Critical</Badge>
            )}
            {highCount > 0 && (
              <Badge className="bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300">
                {highCount} High
              </Badge>
            )}
          </div>
        }
      />

      <div className="bg-card rounded-xl border p-5">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2 px-3 font-medium text-muted-foreground">Service</th>
                <th className="text-center py-2 px-3 font-medium text-muted-foreground">Migration</th>
                <th className="text-center py-2 px-3 font-medium text-muted-foreground">Architecture</th>
                <th className="text-center py-2 px-3 font-medium text-muted-foreground">Dependency</th>
                <th className="text-center py-2 px-3 font-medium text-muted-foreground">Overall</th>
                <th className="text-left py-2 px-3 font-medium text-muted-foreground">Risk Factors</th>
                <th className="text-left py-2 px-3 font-medium text-muted-foreground">Mitigation</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} className="border-b last:border-0 hover:bg-accent/50 transition-colors">
                  <td className="py-2.5 px-3 font-medium text-foreground">{entry.service}</td>
                  <td className="py-2.5 px-3 text-center"><RiskCell level={entry.migrationRisk} /></td>
                  <td className="py-2.5 px-3 text-center"><RiskCell level={entry.architecturalRisk} /></td>
                  <td className="py-2.5 px-3 text-center"><RiskCell level={entry.dependencyRisk} /></td>
                  <td className="py-2.5 px-3 text-center">
                    <span className={cn('px-2 py-0.5 rounded-full text-xs font-bold', riskColors[entry.overallRisk])}>
                      {entry.overallRisk.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-2.5 px-3">
                    {entry.riskFactors.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {entry.riskFactors.map((f, i) => (
                          <Badge key={i} variant="outline" className="text-[10px]">{f}</Badge>
                        ))}
                      </div>
                    ) : (
                      <span className="text-muted-foreground">None</span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-muted-foreground">{entry.mitigation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
