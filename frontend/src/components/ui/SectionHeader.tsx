import { cn } from '@/utils/cn';

interface SectionHeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function SectionHeader({ title, description, action, className, size = 'md' }: SectionHeaderProps) {
  return (
    <div className={cn('flex items-start justify-between gap-4', className)}>
      <div className="min-w-0">
        <h2 className={cn(
          'text-foreground font-semibold tracking-tight',
          size === 'sm' && 'text-sm',
          size === 'md' && 'text-base',
          size === 'lg' && 'text-lg',
        )}>
          {title}
        </h2>
        {description && (
          <p className={cn('text-muted-foreground mt-0.5', size === 'sm' ? 'text-xs' : 'text-sm')}>
            {description}
          </p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
