import { Users, Clock, Link, TrendingUp, AlertTriangle } from 'lucide-react';
import { cn } from '@/utils/cn';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { Badge } from '@/components/ui/Badge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import type { EnhancedRecommendation } from '@/types/results';

const priorityColors = {
  critical: 'border-l-red-500',
  high: 'border-l-orange-500',
  medium: 'border-l-yellow-500',
  low: 'border-l-blue-500',
};

const priorityBadge = {
  critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  low: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
};

export function MicroserviceRecommendations({ recommendations }: { recommendations: EnhancedRecommendation[] }) {
  if (recommendations.length === 0) {
    return (
      <section>
        <SectionHeader title="Microservice Recommendations" description="AI-powered extraction and decomposition recommendations" />
        <div className="bg-card rounded-xl border p-8 text-center">
          <p className="text-muted-foreground">No recommendations available.</p>
        </div>
      </section>
    );
  }

  return (
    <section>
      <SectionHeader
        title="Microservice Recommendations"
        description={`${recommendations.length} AI-powered recommendations`}
        action={
          <Badge variant="outline">
            {recommendations.filter((r) => r.priority === 'critical').length} critical
          </Badge>
        }
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {recommendations.map((rec) => (
          <article
            key={rec.id}
            className={cn('bg-card rounded-xl border p-5 border-l-4 hover:shadow-md transition-all', priorityColors[rec.priority])}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', priorityBadge[rec.priority])}>
                  {rec.priority.toUpperCase()}
                </span>
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300">
                  {rec.category}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">{rec.confidence}%</span>
            </div>
            <h3 className="font-semibold text-foreground text-sm mb-1">{rec.title}</h3>
            <p className="text-xs text-muted-foreground mb-3">{rec.description}</p>

            <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
              <div className="flex items-center gap-1.5">
                <Users className="w-3 h-3 text-muted-foreground" />
                <span className="text-muted-foreground">Engineers:</span>
                <span className="font-medium text-foreground">{rec.estimatedEngineers}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Clock className="w-3 h-3 text-muted-foreground" />
                <span className="text-muted-foreground">Duration:</span>
                <span className="font-medium text-foreground">{rec.estimatedDuration}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <TrendingUp className="w-3 h-3 text-muted-foreground" />
                <span className="text-muted-foreground">ROI:</span>
                <span className="font-medium text-foreground">{rec.expectedROI}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-muted-foreground">Capability:</span>
                <span className="font-medium text-foreground">{rec.businessCapability}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
              <div><span className="text-muted-foreground">Business:</span> <span className="text-foreground">{rec.businessValue}</span></div>
              <div><span className="text-muted-foreground">Technical:</span> <span className="text-foreground">{rec.technicalImpact}</span></div>
            </div>

            <div className="mb-3">
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-muted-foreground">Confidence</span>
                <span className="font-medium">{rec.confidence}%</span>
              </div>
              <ProgressBar value={rec.confidence} color="blue" />
            </div>

            {rec.blockingDependencies.length > 0 && (
              <div className="flex items-start gap-1.5 mb-2 text-xs">
                <AlertTriangle className="w-3 h-3 text-yellow-500 mt-0.5" />
                <span className="text-muted-foreground">Blocked by: {rec.blockingDependencies.join(', ')}</span>
              </div>
            )}

            {rec.evidence.length > 0 && (
              <div className="text-xs text-muted-foreground">
                <span className="font-medium">Evidence:</span>
                <ul className="mt-1 space-y-0.5">
                  {rec.evidence.slice(0, 3).map((e, i) => (
                    <li key={i}>• {e}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t mt-3">
              <span>Effort: <span className="font-medium text-foreground">{rec.effort}</span></span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
