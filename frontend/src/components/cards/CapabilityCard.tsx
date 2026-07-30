import React from 'react';
import { Users, ShoppingCart, CreditCard, Package, Bell, Truck } from 'lucide-react';
import { cn } from '@/utils/cn';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { ConfidenceBadge, StatusBadge } from '@/components/ui/StatusBadge';
import type { BusinessCapability } from '@/types/dashboard';

const iconMap: Record<string, React.ElementType> = {
  Users, ShoppingCart, CreditCard, Package, Bell, Truck,
};

const riskColors = {
  low: 'text-green-600',
  medium: 'text-yellow-600',
  high: 'text-red-600',
};

export const CapabilityCard = React.memo(function CapabilityCard({ data }: { data: BusinessCapability }) {
  const Icon = iconMap[data.icon] || Package;
  return (
    <article className="bg-card rounded-xl border p-5 hover:shadow-md transition-all">
      <div className="flex items-center gap-3 mb-3">
        <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center text-white', data.color)}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-semibold text-foreground text-sm">{data.name}</h3>
          <p className="text-xs text-muted-foreground">{data.classes} classes</p>
        </div>
      </div>
      <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{data.description}</p>
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Readiness</span>
          <span className="font-medium">{data.readiness}%</span>
        </div>
        <ProgressBar value={data.readiness} />
        <div className="flex items-center justify-between">
          <span className={cn('text-xs font-medium', riskColors[data.risk])}>
            {data.risk.toUpperCase()} RISK
          </span>
          <ConfidenceBadge value={data.confidence} />
        </div>
        <div className="text-xs text-muted-foreground">
          Recommended: <span className="font-medium text-primary">{data.recommendedService}</span>
        </div>
      </div>
    </article>
  );
});
