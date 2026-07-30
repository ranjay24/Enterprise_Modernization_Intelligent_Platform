import React from 'react';
import { Search, SlidersHorizontal } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { JobExtendedStatus } from '@/types/jobs';
import { STATUS_CONFIG } from '@/types/jobs';

type FilterStatus = 'all' | JobExtendedStatus;

interface JobFiltersProps {
  search: string;
  onSearchChange: (v: string) => void;
  statusFilter: FilterStatus;
  onStatusFilterChange: (v: FilterStatus) => void;
}

const filterOptions: { value: FilterStatus; label: string }[] = [
  { value: 'all', label: 'All' },
  ...Object.entries(STATUS_CONFIG).map(([key, val]) => ({ value: key as FilterStatus, label: val.label })),
];

export function JobFilters({ search, onSearchChange, statusFilter, onStatusFilterChange }: JobFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search projects..."
          className="w-full pl-9 pr-3 py-2 rounded-lg border border-input bg-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
        <SlidersHorizontal className="w-4 h-4 text-muted-foreground shrink-0" />
        {filterOptions.slice(0, 6).map((opt) => (
          <button
            key={opt.value}
            onClick={() => onStatusFilterChange(opt.value)}
            className={cn(
              'px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors',
              statusFilter === opt.value
                ? 'bg-primary/10 text-primary border border-primary/20'
                : 'bg-muted text-muted-foreground hover:bg-accent border border-transparent'
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
