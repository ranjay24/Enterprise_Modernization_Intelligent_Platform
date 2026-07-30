import { cn } from '@/utils/cn';

const colors: Record<string, string> = {
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

export function RiskBadge({ risk }: { risk: string }) {
  return (
    <span className={cn('px-2 py-1 rounded-full text-xs font-medium', colors[risk] || colors.medium)}>
      {risk.toUpperCase()}
    </span>
  );
}
