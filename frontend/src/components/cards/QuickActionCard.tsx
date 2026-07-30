import React from 'react';
import { Link } from 'react-router-dom';
import { Upload, Briefcase, Network, FileText } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { QuickAction } from '@/types/dashboard';

const iconMap: Record<string, React.ElementType> = {
  Upload, Briefcase, Network, FileText,
};

const colorBg = {
  blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 group-hover:bg-blue-200 dark:group-hover:bg-blue-800/40',
  green: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 group-hover:bg-green-200 dark:group-hover:bg-green-800/40',
  purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 group-hover:bg-purple-200 dark:group-hover:bg-purple-800/40',
  orange: 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 group-hover:bg-orange-200 dark:group-hover:bg-orange-800/40',
};

export const QuickActionCard = React.memo(function QuickActionCard({ data }: { data: QuickAction }) {
  const Icon = iconMap[data.icon] || Upload;
  return (
    <Link to={data.href}>
      <article className="bg-card rounded-xl border p-5 hover:shadow-md transition-all group cursor-pointer">
        <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center mb-3 transition-colors', colorBg[data.color])}>
          <Icon className="w-6 h-6" />
        </div>
        <h3 className="font-semibold text-foreground text-sm mb-1">{data.title}</h3>
        <p className="text-xs text-muted-foreground">{data.description}</p>
      </article>
    </Link>
  );
});
