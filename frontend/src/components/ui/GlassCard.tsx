import { cn } from '@/utils/cn';

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  glow?: 'blue' | 'purple' | 'none';
  hover?: boolean;
}

function GlassCard({ className, glow = 'blue', hover = true, children, ...props }: GlassCardProps) {
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-xl',
        'bg-[var(--bg-glass)] backdrop-blur-xl',
        'shadow-glass',
        'gradient-border',
        glow === 'blue' && 'glow-blue',
        glow === 'purple' && 'glow-purple',
        hover && 'transition-all duration-[var(--duration-base)] ease-[var(--ease-out)] hover:-translate-y-0.5 hover:shadow-lg',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

function GlassCardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex flex-col gap-1 p-6 pb-0', className)} {...props} />;
}

function GlassCardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn('text-base font-semibold tracking-tight text-[var(--text-primary)]', className)} {...props} />;
}

function GlassCardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-sm text-[var(--text-secondary)]', className)} {...props} />;
}

function GlassCardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-6', className)} {...props} />;
}

export { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardDescription, GlassCardContent };
