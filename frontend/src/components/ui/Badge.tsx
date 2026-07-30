import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/utils/cn';

const badgeVariants = cva(
  'inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground',
        secondary: 'bg-secondary text-secondary-foreground',
        destructive: 'bg-destructive text-destructive-foreground',
        outline: 'border text-foreground',
        success: 'bg-success-bg text-success',
        warning: 'bg-warning-bg text-warning',
        danger: 'bg-danger-bg text-danger',
        info: 'bg-info-bg text-info',
        neutral: 'bg-muted text-muted-foreground',
        premium: 'bg-gradient-to-r from-[hsl(var(--stage-ai-boundaries))] to-[hsl(var(--stage-ai-adrs))] text-white',
      },
      size: {
        default: 'px-2 py-0.5 text-[11px]',
        sm: 'px-1.5 py-0 text-[10px]',
        lg: 'px-3 py-1 text-xs',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {
  dot?: boolean;
}

export function Badge({ className, variant, size, dot, children, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props}>
      {dot && (
        <span className={cn(
          'mr-1.5 inline-block h-1.5 w-1.5 rounded-full',
          variant === 'success' && 'bg-success',
          variant === 'warning' && 'bg-warning',
          variant === 'danger' && 'bg-danger',
          variant === 'info' && 'bg-info',
          variant === 'default' && 'bg-primary-foreground',
          (!variant || variant === 'secondary' || variant === 'outline' || variant === 'neutral') && 'bg-current opacity-60',
        )} />
      )}
      {children}
    </div>
  );
}
