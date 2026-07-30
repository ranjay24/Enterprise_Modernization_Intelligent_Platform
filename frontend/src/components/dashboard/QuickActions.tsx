import { Link } from 'react-router-dom';
import type { QuickAction } from '@/types/dashboard';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { cn } from '@/utils/cn';
import { Upload, Briefcase, Network, FileText, ArrowRight } from 'lucide-react';

const iconMap: Record<string, React.ElementType> = {
  Upload, Briefcase, Network, FileText,
};

const colorStyles: Record<string, string> = {
  blue: 'bg-info-bg text-info border-info/20 group-hover:border-info/40',
  green: 'bg-success-bg text-success border-success/20 group-hover:border-success/40',
  purple: 'bg-[hsl(var(--stage-ai-boundaries)/0.1)] text-[hsl(var(--stage-ai-boundaries))] border-[hsl(var(--stage-ai-boundaries)/0.2)] group-hover:border-[hsl(var(--stage-ai-boundaries)/0.4)]',
  orange: 'bg-warning-bg text-warning border-warning/20 group-hover:border-warning/40',
};

export function QuickActions({ data }: { data: QuickAction[] }) {
  return (
    <section>
      <SectionHeader title="Quick Actions" size="lg" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
        {data.map((action) => {
          const Icon = iconMap[action.icon] || Upload;
          return (
            <Link key={action.id} to={action.href}>
              <div className="group rounded-xl border bg-card p-4 hover:shadow-sm transition-all duration-fast cursor-pointer">
                <div className="flex items-center gap-3 mb-0">
                  <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center border transition-colors', colorStyles[action.color])}>
                    <Icon className="w-4.5 h-4.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">{action.title}</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">{action.description}</p>
                  </div>
                  <ArrowRight className="w-4 h-4 text-muted-foreground/40 group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
