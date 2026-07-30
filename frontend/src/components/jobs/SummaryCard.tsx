import React from 'react';
import { cn } from '@/utils/cn';

interface SummaryCardProps {
  icon: React.ElementType;
  label: string;
  value: string | number;
  subtitle?: string;
  color?: string;
  trend?: { value: number; direction: 'up' | 'down' | 'neutral' };
}

export function SummaryCard({ icon: Icon, label, value, subtitle, color = 'text-primary', trend }: SummaryCardProps) {
  return (
    <div className="rounded-xl border bg-card p-4 transition-all duration-fast hover:shadow-sm">
      <div className="flex items-start justify-between mb-2">
        <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center', color)}>
          <Icon className="w-4.5 h-4.5" />
        </div>
        {trend && (
          <span className={cn(
            'text-[10px] font-medium px-1.5 py-0.5 rounded',
            trend.direction === 'up' && 'bg-success-bg text-success',
            trend.direction === 'down' && 'bg-danger-bg text-danger',
            trend.direction === 'neutral' && 'bg-muted text-muted-foreground'
          )}>
            {trend.direction === 'up' ? '↑' : trend.direction === 'down' ? '↓' : '—'} {Math.abs(trend.value)}%
          </span>
        )}
      </div>
      <p className="text-xl font-bold text-foreground tabular-nums leading-tight">{value}</p>
      <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
      {subtitle && <p className="text-[10px] text-muted-foreground/70 mt-0.5">{subtitle}</p>}
    </div>
  );
}
