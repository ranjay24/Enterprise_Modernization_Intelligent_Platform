import { cn } from '@/utils/cn';
import { getScore } from '@/utils/formatters';

interface ScoreGaugeProps {
  score: unknown;
  label: string;
  weight?: number;
  className?: string;
}

export function ScoreGauge({ score: rawScore, label, weight, className }: ScoreGaugeProps) {
  const score = getScore(rawScore);
  const color =
    score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-yellow-500' : 'bg-red-500';
  const textColor =
    score >= 70 ? 'text-green-600' : score >= 40 ? 'text-yellow-600' : 'text-red-600';

  return (
    <div className={cn('bg-card rounded-xl border p-4', className)}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-card-foreground">{label}</span>
        {weight !== undefined && (
          <span className="text-xs text-muted-foreground">{weight}%</span>
        )}
      </div>
      <div className={cn('text-2xl font-bold mb-2', textColor)}>{score}/100</div>
      <div className="w-full bg-muted rounded-full h-2">
        <div className={cn(color, 'h-2 rounded-full transition-all')} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}
