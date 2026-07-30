import { cn } from '@/utils/cn';

interface ProgressBarProps {
  value: number;
  max?: number;
  className?: string;
  color?: 'green' | 'yellow' | 'red' | 'blue';
}

const barColors = {
  green: 'bg-green-500',
  yellow: 'bg-yellow-500',
  red: 'bg-red-500',
  blue: 'bg-primary',
};

function getColor(value: number): 'green' | 'yellow' | 'red' {
  if (value >= 70) return 'green';
  if (value >= 40) return 'yellow';
  return 'red';
}

export function ProgressBar({ value, max = 100, className, color }: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const resolvedColor = color || getColor(value);

  return (
    <div className={cn('w-full bg-muted rounded-full h-2', className)} role="progressbar" aria-valuenow={value} aria-valuemax={max}>
      <div className={cn('h-2 rounded-full transition-all duration-600', barColors[resolvedColor])} style={{ width: `${pct}%` }} />
    </div>
  );
}
