import { cn } from '@/utils/cn';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
  variant?: 'default' | 'compact' | 'card';
}

export function EmptyState({ icon, title, description, action, className, variant = 'default' }: EmptyStateProps) {
  if (variant === 'compact') {
    return (
      <div className={cn('flex flex-col items-center justify-center py-8 text-center', className)}>
        {icon || <Inbox className="w-8 h-8 text-muted-foreground/60 mb-3" />}
        <p className="text-sm font-medium text-foreground">{title}</p>
        {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
        {action && <div className="mt-3">{action}</div>}
      </div>
    );
  }

  if (variant === 'card') {
    return (
      <div className={cn('rounded-xl border bg-card p-8 text-center', className)}>
        {icon || <Inbox className="w-10 h-10 text-muted-foreground/60 mx-auto mb-4" />}
        <h4 className="font-semibold text-foreground mb-1">{title}</h4>
        {description && <p className="text-sm text-muted-foreground mb-4 max-w-sm mx-auto">{description}</p>}
        {action}
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col items-center justify-center py-20 text-center', className)}>
      <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mb-5">
        {icon || <Inbox className="w-8 h-8 text-muted-foreground/60" />}
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-1.5">{title}</h3>
      {description && <p className="text-sm text-muted-foreground mb-5 max-w-md">{description}</p>}
      {action}
    </div>
  );
}
