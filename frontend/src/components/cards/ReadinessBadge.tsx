import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { cn } from '@/utils/cn';

const config = {
  green: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-800 dark:text-green-300', icon: CheckCircle, label: 'Ready' },
  yellow: { bg: 'bg-yellow-100 dark:bg-yellow-900/30', text: 'text-yellow-800 dark:text-yellow-300', icon: AlertTriangle, label: 'Caution' },
  red: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-800 dark:text-red-300', icon: XCircle, label: 'High Risk' },
};

export function ReadinessBadge({ readiness }: { readiness: string }) {
  const c = config[readiness as keyof typeof config] || config.yellow;
  const Icon = c.icon;
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium', c.bg, c.text)}>
      <Icon className="w-3 h-3" />
      {c.label}
    </span>
  );
}
